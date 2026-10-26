# Design Document: Setup Mock SAP Service

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | setup-mock-sap-service                        |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `FastAPI Mock Server`, `docker-compose.yaml`  |

## Context
Pada fase 1 hingga fase 4, seluruh fungsionalitas modul Odoo `wms_sap_connector` (master data sync, inbound PO receipt, putaway allocation, surat jalan report, fleet management, proof of delivery, dan goods receipt/issue webhook) telah selesai dibangun dan diuji menggunakan mock unit testing berbasis *unittest.mock*. Untuk mendukung tahapan demonstrasi, pengujian integrasi manual (*QA testing*), serta simulasi *End-to-End* (E2E), sistem memerlukan layanan eksternal nyata yang berdiri sendiri (*standalone mock service*) untuk mereplikasi sistem SAP Upper Line secara dinamis tanpa memerlukan lisensi enterprise SAP nyata.

## Goals / Non-Goals

### Goals
- Membangun skrip Python mandiri berbasis **FastAPI** (`mock_sap_server.py`) yang dapat dijalankan secara langsung via CLI (`python3 mock_sap_server.py`) atau melalui Docker Compose.
- Menyediakan antarmuka Swagger UI interaktif di `http://localhost:8000/docs` untuk visualisasi dan eksekusi pengujian API.
- Menyediakan endpoint receiver webhook konfirmasi Odoo ke SAP (`POST /api/sap/goods-receipt` dan `POST /api/sap/goods-issue`) yang menghasilkan respons simulasi akuntansi keuangan realistis (`sap_accounting_log`).
- Menyediakan endpoint trigger pengiriman data dari SAP ke Odoo (`POST /api/trigger/master-data`, `POST /api/trigger/inbound-po`, `POST /api/trigger/outbound-delivery`) untuk memicu pembuatan record transaksi pada Odoo secara otomatis.
- Menyediakan endpoint inspeksi riwayat audit `GET /api/sap/history` untuk memantau aliran data dua arah secara transparan.
- Menambahkan deklarasi kontainer layanan `mock-sap` pada `docker-compose.yaml` yang terhubung ke jaringan `wms-network`.

### Non-Goals
- Tidak mengimplementasikan basis data relasional berat (Postgres/Oracle) untuk mock server; data riwayat dan dokumen disimpan secara *in-memory* dengan struktur thread-safe.
- Tidak mengubah logika bisnis inti atau model data internal Odoo pada modul `wms_sap_connector`.
- Tidak mengimplementasikan protokol integrasi selain RESTful JSON (seperti SAP RFC, IDoc, atau SOAP).

## Decisions (ADR)

### 1. Framework Choice: FastAPI with Pydantic & Uvicorn
- **Rationale:** FastAPI merupakan framework Python modern berkinerja tinggi yang secara otomatis menghasilkan dokumentasi interaktif OpenAPI/Swagger UI (`/docs`) dan skema validasi tipe data berbasis Pydantic. Hal ini sangat memudahkan tim pengembang dan QA untuk melakukan pengujian manual tanpa perlu mengimpor koleksi Postman pihak ketiga.
- **Alternatives Considered:**
  - Flask: Membutuhkan dependensi tambahan untuk Swagger UI (Flasgger) dan kode boilerplate validasi data yang lebih panjang.
  - WireMock / Mockoon: Berjalan di luar ekosistem Python dan sulit dikustomisasi dengan logika dinamis seperti kalkulasi simulasi jurnal akuntansi PPN dan HPP.
- **Consequences:** Memerlukan pustaka `fastapi`, `uvicorn`, `requests`, dan `pydantic` pada lingkungan virtual host atau kontainer runner.

### 2. Dual-Mode Deployment (Host CLI & Docker Compose Service)
- **Rationale:** Selama proses pengujian, pengembang mungkin ingin menjalankan mock server secara cepat di terminal lokal (`uvicorn mock_sap_server:app --port 8000`) atau menjalankannya sebagai bagian dari stack kontainer Docker (`docker compose up mock-sap`).
- **Alternatives Considered:**
  - Hanya mendukung Docker: Memperlambat loop debugging jika pengembang ingin mengedit skrip mock server secara instan.
- **Consequences:** Skrip dirancang dengan *environment variable fallback* (`PORT`, `ODOO_BASE_URL`, `SAP_API_TOKEN`) sehingga dapat membaca konfigurasi host maupun jaringan kontainer (`http://odoo:8069` vs `http://localhost:8070`).

### 3. Realistic Accounting Journal Simulation Engine
- **Rationale:** Dalam spesifikasi bisnis [tsd.md](../../docs/tsd.md) Bagian 3.5, Odoo merekam objek `sap_accounting_log` dari respons webhook SAP ke dalam `sap.sync.log`. Simulator harus menghasilkan data finansial yang realistis (nomor jurnal unik berformat `JE-SAP-YYYY-XXXX`, tanggal posting aktual, akun debit/kredit, dan status POSTED).
- **Alternatives Considered:**
  - Mengembalikan teks statis sederhana: Tidak memvalidasi kemampuan parsing JSON dan ekstraksi data audit pada modul Odoo.
- **Consequences:** Dibuat modul generator jurnal akuntansi di dalam skrip mock server yang memproduksi struktur JSON sesuai kontrak SSOT.

## Technical Architecture & Data Schema

### 1. Struktur Arsitektur Layanan Mock Server (`mock_sap_server.py`)

```python
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field
import uvicorn
import requests
import os
import uuid
from datetime import datetime

app = FastAPI(
    title="SAP Upper Line Mock Service",
    description="Simulator API Two-Tier WMS & Logistics Execution System",
    version="1.0.0",
)
```

### 2. Definisi Skema Data (Pydantic Models)

- **Goods Receipt Webhook:**
  - Input: `sap_doc_number` (str), `status` (str), `received_date` (str), `warehouse_code` (str).
  - Output: `status` (str), `code` (int), `message` (str), `sap_accounting_log` (dict).
- **Goods Issue Webhook:**
  - Input: `sap_doc_number` (str), `status` (str), `issued_date` (str), `receiver_name` (str), `has_pod` (bool).
  - Output: `status` (str), `code` (int), `message` (str), `sap_accounting_log` (dict).
- **Trigger Payload Models:**
  - Master Material & Partner Item Models.
  - Inbound PO Request Model.
  - Outbound Delivery Request Model.

### 3. Konfigurasi Docker Compose (`docker-compose.yaml`)

```yaml
  mock-sap:
    container_name: wms-mock-sap
    build:
      context: .
      dockerfile: Dockerfile.mock_sap
    ports:
      - "8000:8000"
    environment:
      - PORT=8000
      - SAP_API_TOKEN=secret_sap_token_123
      - ODOO_BASE_URL=http://odoo:8069
    networks:
      - wms-network
    depends_on:
      - odoo
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Konflik port 8000 pada mesin lokal pengguna | Low | Variabel lingkungan `PORT` / `MOCK_SAP_PORT` memungkinkan pemetaan port alternatif (misal: 8008 atau 8080). |
| Ketergantungan pustaka FastAPI pada host | Low | Menyediakan `Dockerfile.mock_sap` mandiri berbasis `python:3.10-slim` sehingga pengguna tidak diwajibkan menginstal pustaka secara global di host machine jika menggunakan Docker. |
| Perbedaan URL Odoo pada Docker vs Localhost | Medium | Logika resolusi cerdas pada skrip: jika `ODOO_BASE_URL` tidak ditentukan, memeriksa apakah host berjalan dalam kontainer atau lokal, dengan fallback ke `http://localhost:8070`. |

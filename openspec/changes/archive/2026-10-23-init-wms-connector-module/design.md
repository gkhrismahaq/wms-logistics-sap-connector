# Design Document: Init Wms Connector Module

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | init-wms-connector-module                     |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `ir.module.module`                            |

## Context
Proyek ini mengadopsi pola *Two-Tier ERP* di mana SAP bertindak sebagai *Upper Line* dan Odoo 17 bertindak sebagai *Bottom Line* untuk eksekusi pergudangan dan logistik fisik. Untuk memulai siklus pengembangan, Odoo memerlukan modul custom yang terisolasi di direktori `addons/wms_sap_connector` dengan file manifest `__manifest__.py` yang valid agar dapat dikenali dan dimuat oleh server Odoo.
> **Reference:** Lihat [proposal.md](proposal.md) dan [tsd.md](../../docs/tsd.md) — Bagian 3.1.

## Goals / Non-Goals
### Goals
- Menginisialisasi struktur direktori modul Odoo 17 pada path `addons/wms_sap_connector`.
- Membuat file `addons/wms_sap_connector/__init__.py` kosong yang valid untuk sintaks Python package.
- Membuat file manifest `addons/wms_sap_connector/__manifest__.py` berstandar Odoo 17 dengan deklarasi dependensi wajib: `base`, `stock`, dan `delivery`.
- Memastikan modul dapat dideteksi dan diinstal oleh Odoo tanpa memicu syntax error atau dependency error.

### Non-Goals
- Pembuatan model data ORM baru atau penambahan field custom (akan dikerjakan pada change fase berikutnya seperti `create-sync-log-model`).
- Pembuatan view XML, menu navigasi, atau konfigurasi hak akses security (akan dikerjakan pada change UI & Security berikutnya).
- Pembuatan REST API endpoint atau integrasi webhook (akan dikerjakan pada change Fase 2).

## Decisions (ADR)
### 1. Struktur Modul Tunggal Terpusat (`wms_sap_connector`)
- **Rationale:** Seluruh logika WMS logistik dan konektor SAP disatukan ke dalam satu modul Odoo (`wms_sap_connector`) dengan subdirektori modular (`models/`, `views/`, `controllers/`, `security/`) guna memudahkan pengelolaan dependensi, deployment kontainer Docker, dan upgrade modul via `make addon wms_sap_connector`.
- **Alternatives Considered:** Memisahkan modul menjadi dua addon terpisah (misalnya `wms_base` dan `wms_sap_connector`). Opsi ini ditolak karena meningkatkan overhead manajemen manifest dan dependensi pada tahap awal pengembangan.
- **Consequences:** Modul harus memiliki pengorganisasian internal yang sangat rapi untuk mencegah tumpang tindih tanggung jawab kode (*separation of concerns*).

### 2. Deklarasi Dependensi Wajib (`base`, `stock`, `delivery`)
- **Rationale:** Modul ini secara langsung memperluas model bawaan Odoo seperti `stock.picking`, `stock.location`, dan fungsionalitas pengiriman. Menetapkan dependensi ini di manifest menjamin bahwa Odoo akan memuat seluruh modul inti tersebut sebelum modul custom diinisialisasi.
- **Alternatives Considered:** Hanya mendeklarasikan `base` dan membiarkan user menginstal `stock` secara manual. Opsi ini ditolak karena rentan menimbulkan error *missing model table* saat server dijalankan.
- **Consequences:** Instalasi pertama modul akan membutuhkan waktu pemuatan dependensi standar Odoo, namun menjamin integritas referensi ORM.

## Technical Architecture & Data Schema
Struktur direktori modul awal yang akan dibuat:
```text
addons/
└── wms_sap_connector/
    ├── __init__.py
    └── __manifest__.py
```

Rancangan konten file deskriptor `addons/wms_sap_connector/__manifest__.py`:
```python
# -*- coding: utf-8 -*-
{
    "name": "WMS Logistics SAP Connector",
    "version": "17.0.1.0.0",
    "category": "Inventory/Logistics",
    "summary": "Odoo 17 Two-Tier WMS & Logistics Execution System integrated with SAP Upper Line",
    "author": "Gilang Khrismahaq",
    "website": "https://github.com/gilangkhrismahaq/wms-logistics-sap-connector",
    "license": "LGPL-3",
    "depends": [
        "base",
        "stock",
        "delivery",
    ],
    "data": [],
    "installable": True,
    "application": True,
    "auto_install": False,
}
```

Rancangan konten file inisialisasi package `addons/wms_sap_connector/__init__.py`:
```python
# -*- coding: utf-8 -*-
# Initialization file for wms_sap_connector module
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Kesalahan sintaks pada dictionary manifest `__manifest__.py` | Low | Uji sintaks Python melalui `python3 -m py_compile` dan validasi pemuatan modul Odoo |
| Modul standar `delivery` belum terpasang di database | Low | Manifest otomatis mendownload/menginstal modul `delivery` bawaan Odoo berkat deklarasi `depends` |

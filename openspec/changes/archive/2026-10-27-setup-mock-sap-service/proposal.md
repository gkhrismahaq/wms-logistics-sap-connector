# Proposal: Setup Mock SAP Service

| Field              | Value                                                              |
|--------------------|--------------------------------------------------------------------|
| **Change Name**    | setup-mock-sap-service                                             |
| **Roadmap Phase**  | Fase 5: Simulator SAP & Pengujian End-to-End (Simulation & Verification) |
| **Target Cap.**    | `mock-sap-service`                                                 |
| **Est. Effort**    | 4 Hours                                                            |
| **Risk Level**     | Low                                                                |

## Why
Dalam pengembangan integrasi sistem *Two-Tier ERP* antara Odoo 17 WMS dan SAP Upper Line, pengembang dan tim QA membutuhkan lingkungan uji mandiri yang dapat mereplikasi perilaku SAP secara realistis tanpa ketergantungan pada server SAP produksi yang mahal atau terbatas. Diperlukan sebuah simulator mandiri (*mock service*) berbasis **FastAPI** (`mock_sap_server.py`) yang berjalan pada jaringan lokal atau kontainer Docker, mengekspos dokumentasi Swagger UI interaktif di `http://localhost:8000/docs`, mampu menampung webhook konfirmasi fisik dari Odoo (*Goods Receipt* dan *Goods Issue/POD*), mengembalikan respons simulasi akuntansi keuangan SAP (`sap_accounting_log`), serta menyediakan pemicu pengiriman instruksi data master, PO, dan Delivery Order ke endpoint Odoo.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.5.1, 3.5.2, 3.5.3 dan [roadmap.md](../../docs/roadmap.md) — Fase 5.1.

## What Changes
- **Backend (ORM & Models):**
  - Tidak ada perubahan skema tabel ORM Odoo karena model konektor SAP telah lengkap pada fase sebelumnya.
- **Security & Access Rights:**
  - Penerapan validasi otentikasi token rahasia (`X-Odoo-API-Key` atau `Authorization: Bearer`) pada mock service FastAPI agar protokol keamanan konsisten dengan Odoo.
- **Views & UI:**
  - Antarmuka visual web Swagger UI interaktif bawaan FastAPI pada rute `/docs` dan ReDoc pada `/redoc` untuk mempermudah eksekusi manual dan simulasi pengujian.
- **Integration & API:**
  - Pembuatan skrip server mandiri `mock_sap_server.py` berbasis FastAPI & Uvicorn.
  - Implementasi endpoint receiver webhook Odoo ke SAP:
    - `POST /api/sap/goods-receipt`: Menerima konfirmasi penerimaan kargo PO dari Odoo dan mengembalikan simulasi jurnal pemotongan hutang & persediaan masuk (`sap_accounting_log`).
    - `POST /api/sap/goods-issue`: Menerima konfirmasi serah terima kargo Surat Jalan & POD dari Odoo dan mengembalikan simulasi jurnal pemotongan HPP & persediaan barang jadi (`sap_accounting_log`).
  - Implementasi endpoint pemicu (trigger) SAP ke Odoo:
    - `POST /api/trigger/master-data`: Menembakkan payload sinkronisasi produk/partner ke Odoo `/api/sap/master`.
    - `POST /api/trigger/inbound-po`: Menembakkan instruksi pesanan pembelian ke Odoo `/api/sap/inbound/po`.
    - `POST /api/trigger/outbound-delivery`: Menembakkan instruksi pengiriman kargo ke Odoo `/api/sap/outbound/delivery`.
  - Endpoint audit dan inspeksi:
    - `GET /api/sap/history`: Menampilkan riwayat transaksi webhook yang diterima dan trigger yang dikirim untuk verifikasi pengujian end-to-end.
    - `GET /health`: Pemeriksaan kesehatan layanan (*health check*).
  - Integrasi layanan kontainer ke dalam `docker-compose.yaml` di bawah nama layanan `mock-sap` pada jaringan `wms-network`.

## Capabilities
### New Capabilities
- `mock-sap-service`: Penyediaan simulator mandiri berbasis FastAPI yang mereplikasi API dan webhook SAP Upper Line untuk verifikasi integrasi dua arah Odoo WMS.

### Modified Capabilities
- `None`

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `mock_sap_server.py`
  - `Dockerfile.mock_sap`
  - `tests/test_mock_sap_server.py`
- **Files to Modify:**
  - `docker-compose.yaml`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 3.5)
  - `docs/roadmap.md` (Capability 5.1: `mock-sap-service`)
- **Estimated Effort:** 4 jam.
- **Complexity & Risk Analysis:** Kompleksitas rendah. Risiko utama adalah konflik port jika port 8000 sudah digunakan pada mesin host. Mitigasi dilakukan dengan menyediakan konfigurasi port lingkungan melalui variabel `PORT` atau `MOCK_SAP_PORT`.

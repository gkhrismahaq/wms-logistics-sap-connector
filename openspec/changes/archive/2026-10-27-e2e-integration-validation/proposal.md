# Proposal: E2E Integration Validation

| Field              | Value                                                              |
|--------------------|--------------------------------------------------------------------|
| **Change Name**    | e2e-integration-validation                                         |
| **Roadmap Phase**  | Fase 5: Simulator SAP & Pengujian End-to-End (Simulation & Verification) |
| **Target Cap.**    | `mock-sap-service`                                                 |
| **Est. Effort**    | 4 Hours                                                            |
| **Risk Level**     | Low                                                                |

## Why
Setelah seluruh kapabilitas fungsional modul Odoo `wms_sap_connector` (Fase 1 hingga Fase 4) dan layanan simulator SAP mandiri berbasis FastAPI (`mock_sap_server.py`) selesai dibangun dan diuji secara terisolasi, langkah krusial berikutnya adalah melakukan verifikasi integrasi dua arah secara menyeluruh (*End-to-End / E2E Integration Testing*). Pengujian ini memastikan bahwa seluruh komponen sistem Two-Tier ERP bekerja secara harmonis, mulai dari dorongan master data material & partner dari SAP ke Odoo, siklus pesanan pembelian masuk (*Inbound PO*) hingga validasi *Goods Receipt* dan simulasi jurnal akuntansi masuk, alokasi penempatan otomatis (*Putaway Rule*), penerbitan pesanan pengiriman (*Outbound Delivery*), penugasan armada dan pencetakan Surat Jalan, hingga unggah bukti serah terima (*Proof of Delivery*) dan pelaporan balik *Goods Issue* ke SAP.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 5.1.

## What Changes
- **Backend (ORM & Models):**
  - Tidak ada perubahan skema data tabel inti karena model `wms_sap_connector` telah lengkap pada fase sebelumnya.
- **Security & Access Rights:**
  - Validasi otentikasi menyeluruh pada token integrasi (`X-Odoo-API-Key` dan `Authorization: Bearer`) dalam pengujian end-to-end, memastikan kontrol akses multi-role (Staf Gudang, Dispatcher, Supir, SAP Integration Service) berjalan sesuai spesifikasi.
- **Views & UI:**
  - Verifikasi tampilan Surat Jalan PDF QWeb dan status visual log sinkronisasi `sap.sync.log` serta antarmuka Swagger UI interaktif pada mock server.
- **Integration & API:**
  - Pembuatan automated integration test suite berbasis Odoo `HttpCase` / `TransactionCase` pada `addons/wms_sap_connector/tests/test_e2e_integration.py` yang mensimulasikan alur penuh Two-Tier WMS & SAP.
  - Pembuatan skrip verifikasi E2E mandiri `tests/verify_e2e_integration.py` yang mengeksekusi integrasi langsung antara kontainer Odoo (`http://localhost:8070` atau `http://odoo:8069`) dan kontainer Mock SAP (`http://localhost:8000` atau `http://mock-sap:8000`).

## Capabilities
### New Capabilities
- `None`

### Modified Capabilities
- `mock-sap-service`: Penambahan spesifikasi validasi integrasi komprehensif dua arah (E2E) antara Odoo 17 WMS dan SAP Upper Line Mock Service yang mencakup siklus lengkap operasional logistik dan rekonsiliasi finansial.

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/tests/test_e2e_integration.py`
  - `tests/verify_e2e_integration.py`
- **Files to Modify:**
  - `None`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 2.2, 3.5)
  - `docs/roadmap.md` (Capability 5.1: `mock-sap-service`, Change: `e2e-integration-validation`)
- **Estimated Effort:** 4 jam.
- **Complexity & Risk Analysis:** Kompleksitas rendah hingga menengah. Risiko utama adalah dependensi kesiapan konektivitas jaringan antara Odoo dan Mock SAP server. Mitigasi dilakukan dengan menyediakan mekanisme healthcheck pra-eksekusi serta isolasi pengujian mock pada suite unit test internal Odoo.

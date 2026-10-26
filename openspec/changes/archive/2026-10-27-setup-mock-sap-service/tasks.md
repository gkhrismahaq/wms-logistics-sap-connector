# Implementation Tasks: Setup Mock SAP Service

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...` or project root files)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Mendefinisikan skema data Pydantic untuk request, response, dan payload jurnal akuntansi `sap_accounting_log` pada `mock_sap_server.py`
- [x] 1.2 [Backend] Mengimplementasikan generator simulasi jurnal akuntansi keuangan SAP dan penyimpanan riwayat transaksi in-memory pada `mock_sap_server.py`

## 2. Security & Access Control
- [x] 2.1 [Security] Mengimplementasikan dependency validasi otentikasi token API (`X-Odoo-API-Key` dan `Authorization: Bearer`) pada `mock_sap_server.py`
- [x] 2.2 [Security] Menambahkan penanganan penolakan otorisasi HTTP 401 untuk akses tidak sah pada `mock_sap_server.py`

## 3. User Interface & Views
- [x] 3.1 [UI] Mengonfigurasi metadata aplikasi FastAPI, rute dokumentasi Swagger UI (`/docs`), ReDoc (`/redoc`), dan deskripsi skema OpenAPI pada `mock_sap_server.py`
- [x] 3.2 [UI] Menyediakan endpoint healthcheck `GET /health` dan `GET /` dengan metadata status layanan pada `mock_sap_server.py`

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [Integration] Mengimplementasikan endpoint receiver webhook Odoo ke SAP (`POST /api/sap/goods-receipt` dan `POST /api/sap/goods-issue`) pada `mock_sap_server.py`
- [x] 4.2 [Integration] Mengimplementasikan endpoint trigger pengiriman SAP ke Odoo (`POST /api/trigger/master-data`, `POST /api/trigger/inbound-po`, `POST /api/trigger/outbound-delivery`) pada `mock_sap_server.py`
- [x] 4.3 [Integration] Mengimplementasikan endpoint inspeksi dan reset riwayat transaksi `GET /api/sap/history` dan `DELETE /api/sap/history` pada `mock_sap_server.py`
- [x] 4.4 [Integration] Membuat berkas `Dockerfile.mock_sap` dan mendaftarkan layanan kontainer `mock-sap` pada `docker-compose.yaml`

## 5. Verification & Testing
- [x] 5.1 [Test] Menuliskan suite pengujian unit mandiri berbasis `pytest` dan `TestClient` untuk seluruh endpoint mock server pada `tests/test_mock_sap_server.py`
- [x] 5.2 [Test] Menjalankan eksekusi pengujian `pytest tests/test_mock_sap_server.py`, verifikasi modul Odoo, serta linter `ruff check .` untuk memastikan 0 failure dan 0 error

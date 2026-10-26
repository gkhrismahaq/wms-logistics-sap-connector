# Implementation Tasks: API Receive SAP Master Data

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Inisialisasi direktori controller dan file `addons/wms_sap_connector/controllers/__init__.py`
- [x] 1.2 [Backend] Daftarkan package controller ke dalam file inisialisasi utama modul `addons/wms_sap_connector/__init__.py`

## 2. Security & Access Control
- [x] 2.1 [Security] Implementasikan fungsi verifikasi otentikasi API Key (`X-Odoo-API-Key` / Bearer token) terhadap konfigurasi `wms_sap_connector.sap_api_token` pada `addons/wms_sap_connector/controllers/main.py`
- [x] 2.2 [Security] Pastikan isolasi eksekusi ORM controller menggunakan hak `sudo()` terisolasi untuk pembuatan dan pembaruan master data

## 3. User Interface & Views
- [x] 3.1 [UI] Verifikasi integrasi tampilan record yang disinkronkan dengan formulir produk (`addons/wms_sap_connector/views/product_template_views.xml`) dan kontak (`addons/wms_sap_connector/views/res_partner_views.xml`)
- [x] 3.2 [UI] Verifikasi keterlihatan log transaksi master data pada antarmuka audit log (`addons/wms_sap_connector/views/sap_sync_log_views.xml`)

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [Integration] Implementasikan Odoo Controller `addons/wms_sap_connector/controllers/main.py` dengan rute `POST /api/sap/master` bertipe JSON
- [x] 4.2 [Integration] Implementasikan logika pemrosesan idempotent upsert untuk master material produk (`master_type == 'product'`) lengkap dengan konversi string Base64 ke `image_1920` pada `addons/wms_sap_connector/controllers/main.py`
- [x] 4.3 [Integration] Implementasikan logika pemrosesan idempotent upsert untuk master mitra bisnis (`master_type == 'partner'`) dengan klasifikasi `supplier_rank` / `customer_rank` pada `addons/wms_sap_connector/controllers/main.py`
- [x] 4.4 [Integration] Implementasikan pencatatan otomatis audit log setiap request dan respons ke model `sap.sync.log` pada `addons/wms_sap_connector/controllers/main.py`

## 5. Verification & Testing
- [x] 5.1 [Test] Jalankan uji validasi sintaks Python pada seluruh file controller di `addons/wms_sap_connector/controllers/`
- [x] 5.2 [Test] Lakukan upgrade modul via `make addon wms_sap_connector` dan verifikasi bahwa controller terdaftar pada routing table Odoo
- [x] 5.3 [Test] Lakukan pengujian simulasi API skenario `REQ-MDAPI-01`, `REQ-MDAPI-02`, `REQ-MDAPI-03`, dan `REQ-MDAPI-04` menggunakan curl/HTTP POST (menguji otentikasi token, upsert produk, Base64 image, upsert partner, dan rekaman audit log)

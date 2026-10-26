# Implementation Tasks: API Receive SAP Purchase Order

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Verifikasi ketersediaan dan kesiapan model `stock.picking`, `stock.move`, `res.partner`, dan `product.product` untuk alur pembuatan dokumen inbound PO pada `addons/wms_sap_connector/models/stock_picking.py`

## 2. Security & Access Control
- [x] 2.1 [Security] Pastikan verifikasi token API (`X-Odoo-API-Key` / Bearer) dan eksekusi ORM dengan hak `sudo()` terisolasi diterapkan pada rute inbound PO di `addons/wms_sap_connector/controllers/main.py`

## 3. User Interface & Views
- [x] 3.1 [UI] Verifikasi visibilitas dokumen picking dan baris move yang diterbitkan otomatis melalui API pada antarmuka *Transfers / Receipts* (`addons/wms_sap_connector/views/stock_picking_views.xml`)
- [x] 3.2 [UI] Verifikasi keterlihatan log transaksi inbound PO pada antarmuka audit log (`addons/wms_sap_connector/views/sap_sync_log_views.xml`)

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [Integration] Implementasikan rute REST API `POST /api/sap/inbound/po` bertipe JSON pada `addons/wms_sap_connector/controllers/main.py`
- [x] 4.2 [Integration] Implementasikan logika pemrosesan idempotent receipt creation berdasarkan `sap_doc_number` pada `addons/wms_sap_connector/controllers/main.py`
- [x] 4.3 [Integration] Implementasikan validasi vendor (`sap_partner_code`), pemetaan item material (`sap_material_code`), dan pembentukan baris `stock.move` pada `addons/wms_sap_connector/controllers/main.py`
- [x] 4.4 [Backend] Implementasikan pemanggilan `action_confirm()` otomatis untuk mentransisikan dokumen picking ke status `assigned` pada `addons/wms_sap_connector/controllers/main.py`
- [x] 4.5 [Integration] Implementasikan pencatatan otomatis transaksi sukses maupun gagal dengan tipe `inbound_po` ke model `sap.sync.log` pada `addons/wms_sap_connector/controllers/main.py`

## 5. Verification & Testing
- [x] 5.1 [Test] Jalankan uji kompilasi sintaks Python pada `addons/wms_sap_connector/controllers/main.py`
- [x] 5.2 [Test] Lakukan upgrade modul via `make addon wms_sap_connector` dan verifikasi rute terdaftar pada server Odoo
- [x] 5.3 [Test] Jalankan pengujian simulasi API skenario `REQ-INB-03`, `REQ-INB-04`, dan `REQ-INB-05` menggunakan curl (menguji penolakan 401 tanpa token, pembuatan dokumen picking baru 201, penanganan idempoten 200, validasi error 400, dan pencatatan audit log `sap.sync.log`)

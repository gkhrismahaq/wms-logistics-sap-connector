# Implementation Tasks: Extend Picking Inbound Fields

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Buat file model `addons/wms_sap_connector/models/stock_picking.py` yang mewarisi `stock.picking` dengan field `sap_doc_number` dan `sap_sync_status`
- [x] 1.2 [Backend] Daftarkan model `stock_picking` ke dalam file inisialisasi modul `addons/wms_sap_connector/models/__init__.py`

## 2. Security & Access Control
- [x] 2.1 [Security] Verifikasi hak akses field model bawaan `stock.picking` pada `addons/wms_sap_connector/security/ir.model.access.csv` untuk memastikan keterbacaan oleh grup WMS

## 3. User Interface & Views
- [x] 3.1 [UI] Buat view XML `addons/wms_sap_connector/views/stock_picking_views.xml` untuk menambahkan `sap_doc_number` dan `sap_sync_status` pada form view (`stock.view_picking_form`)
- [x] 3.2 [UI] Tambahkan kolom `sap_doc_number` dan badge `sap_sync_status` pada tree view (`stock.vpicktree`) di `addons/wms_sap_connector/views/stock_picking_views.xml`
- [x] 3.3 [UI] Tambahkan filter pencarian `sap_doc_number` dan group by `sap_sync_status` pada search view (`stock.view_picking_internal_search`) di `addons/wms_sap_connector/views/stock_picking_views.xml`
- [x] 3.4 [Backend] Daftarkan file view `views/stock_picking_views.xml` ke dalam manifest modul `addons/wms_sap_connector/__manifest__.py`

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [Backend] Implementasikan validasi model atau default helper status pada `addons/wms_sap_connector/models/stock_picking.py`
- [x] 4.2 [Integration] Verifikasi kesiapan field referensi SAP model `stock.picking` untuk konsumsi controller inbound API pada `addons/wms_sap_connector/models/stock_picking.py`

## 5. Verification & Testing
- [x] 5.1 [Test] Jalankan uji kompilasi sintaks Python pada `addons/wms_sap_connector/models/stock_picking.py`
- [x] 5.2 [Test] Lakukan upgrade modul via `make addon wms_sap_connector` dan verifikasi bahwa tabel dan kolom database PostgreSQL terbuat
- [x] 5.3 [Test] Jalankan pengujian fungsional skenario `REQ-INB-01` dan `REQ-INB-02` (verifikasi create/write picking dengan `sap_doc_number`, pengecekan copy=False, dan verifikasi tampilan UI)

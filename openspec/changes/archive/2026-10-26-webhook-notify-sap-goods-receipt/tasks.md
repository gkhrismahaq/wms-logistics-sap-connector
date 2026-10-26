# Implementation Tasks: Webhook Notify SAP Goods Receipt

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation

- [x] 1.1 [Backend] Definisikan konstanta endpoint webhook goods receipt dan status payload pada `addons/wms_sap_connector/constants.py`

## 2. Security & Access Control

- [x] 2.1 [Security] Pastikan izin pemanggilan method aksi webhook dan retry pada model `stock.picking` dapat diakses oleh grup `group_wms_operator` dan `group_wms_manager` pada `addons/wms_sap_connector/security/ir.model.access.csv`

## 3. User Interface & Views

- [x] 3.1 [UI] Tambahkan tombol aksi "Retry SAP Webhook" pada header formulir picking `addons/wms_sap_connector/views/stock_picking_views.xml` untuk dokumen done yang belum tersinkron

## 4. Business Logic & Integration Endpoints

- [x] 4.1 [Integration] Implementasikan method transmisi webhook HTTP POST `_send_sap_goods_receipt_webhook` dan method aksi manual `action_send_sap_goods_receipt_webhook` pada `addons/wms_sap_connector/models/stock_picking.py`
- [x] 4.2 [Backend] Hubungkan pemanggilan otomatis webhook pada override method `_action_done` model `stock.picking` di `addons/wms_sap_connector/models/stock_picking.py` lengkap dengan pencatatan respon akuntansi ke `sap.sync.log`

## 5. Verification & Testing

- [x] 5.1 [Test] Jalankan uji kompilasi sintaks Python dan validasi XML views modul pada `addons/wms_sap_connector/` serta upgrade modul via `make addon wms_sap_connector`
- [x] 5.2 [Test] Buat dan jalankan test suite otomatis `test_webhook_goods_receipt.py` pada `addons/wms_sap_connector/tests/` untuk menguji skenario transmisi sukses (`REQ-WHK-01`), pencatatan jurnal akuntansi, dan non-blocking error handling (`REQ-WHK-02`)
- [x] 5.3 [Test] Jalankan pengujian end-to-end transmisi webhook Goods Receipt dan tombol retry pada database Odoo

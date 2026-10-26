# Implementation Tasks: Webhook Notify SAP Goods Issue

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Menambahkan konstanta `REF_PREFIX_GOODS_ISSUE`, `SAP_ENDPOINT_GOODS_ISSUE`, dan `WEBHOOK_STATUS_GOODS_ISSUED` pada file `addons/wms_sap_connector/constants.py`
- [x] 1.2 [Backend] Menambahkan struktur deklarasi method `_send_sap_goods_issue_webhook()` dan `action_send_sap_goods_issue_webhook()` pada model `stock.picking` di `addons/wms_sap_connector/models/stock_picking.py`

## 2. Security & Access Control
- [x] 2.1 [Security] Memverifikasi hak akses tombol aksi manual Goods Issue bagi user grup gudang dan logistik pada `addons/wms_sap_connector/security/ir.model.access.csv`
- [x] 2.2 [Security] Memastikan hak baca dan retry log audit transaksi `sap.sync.log` tetap konsisten pada `addons/wms_sap_connector/security/security.xml`

## 3. User Interface & Views
- [x] 3.1 [UI] Menambahkan tombol header `"Send Goods Issue to SAP"` (`action_send_sap_goods_issue_webhook`) dengan atribut visibilitas dinamis pada formulir `stock.view_picking_form` di `addons/wms_sap_connector/views/stock_picking_views.xml`
- [x] 3.2 [Backend] Memverifikasi integritas pemuatan view XML pada manifest modul `addons/wms_sap_connector/__manifest__.py`

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [Integration] Mengimplementasikan logika pembentukan payload JSON, transmisi HTTP POST ke endpoint SAP, penangkapan respon jurnal HPP `sap_accounting_log`, dan persistensi log audit pada `_send_sap_goods_issue_webhook()` di `addons/wms_sap_connector/models/stock_picking.py`
- [x] 4.2 [Backend] Mengintegrasikan pemanggilan webhook Goods Issue otomatis pada lifecycle hook `_action_done()` untuk dokumen transfer pengeluaran (`outgoing`) yang memiliki `sap_doc_number` dan `has_pod == True` di `addons/wms_sap_connector/models/stock_picking.py`
- [x] 4.3 [Backend] Mengintegrasikan pemanggilan webhook Goods Issue otomatis pada method `write()` saat bukti POD (`proof_of_delivery` / `pod_signed_by`) diunggah pada transfer yang telah berstatus `done` di `addons/wms_sap_connector/models/stock_picking.py`

## 5. Verification & Testing
- [x] 5.1 [Test] Menuliskan unit test komprehensif untuk pengujian transmisi sukses Goods Issue webhook, respon akuntansi, fail-safe error handling, dan retry manual pada `addons/wms_sap_connector/tests/test_webhook_goods_issue.py`
- [x] 5.2 [Backend] Mendaftarkan file pengujian `test_webhook_goods_issue` pada `addons/wms_sap_connector/tests/__init__.py`
- [x] 5.3 [Test] Menjalankan upgrade modul dan eksekusi seluruh suite pengujian Odoo 17 serta linter `ruff check .` untuk memastikan 0 failure dan 0 error

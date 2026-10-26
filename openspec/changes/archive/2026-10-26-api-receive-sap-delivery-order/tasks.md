# Implementation Tasks: API Receive SAP Delivery Order

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Verifikasi keberadaan konstanta `SYNC_TYPE_OUTBOUND_SO` dan `REF_PREFIX_OUTBOUND_SO` pada `addons/wms_sap_connector/constants.py`
- [x] 1.2 [Backend] Implementasikan method ORM `create_outbound_from_sap(payload_dict)` pada model `stock.picking` di `addons/wms_sap_connector/models/stock_picking.py` lengkap dengan validasi field mandatori dan pengecekan idempoten

## 2. Security & Access Control
- [x] 2.1 [Security] Pastikan izin akses pembuatan dan pembaruan `stock.picking` dan `stock.move` dari konteks integrasi controller terlindungi aman pada `addons/wms_sap_connector/security/ir.model.access.csv`

## 3. User Interface & Views
- [x] 3.1 [UI] Pastikan dokumen Delivery Order (`outgoing`) yang diterbitkan dari integrasi SAP dapat divisualisasikan dengan tepat pada form `stock.view_picking_form` di `addons/wms_sap_connector/views/stock_picking_views.xml`

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [Integration] Buat controller kelas `SapOutboundController` dengan endpoint `POST /api/sap/outbound/delivery` pada `addons/wms_sap_connector/controllers/main.py`
- [x] 4.2 [Integration] Hubungkan autentikasi API token, parsing payload, pemanggilan `create_outbound_from_sap`, dan pencatatan audit log `sap.sync.log` pada `addons/wms_sap_connector/controllers/main.py`

## 5. Verification & Testing
- [x] 5.1 [Test] Lakukan kompilasi sintaks Python dengan `python3 -m py_compile` pada seluruh file Python di `addons/wms_sap_connector/` dan upgrade modul Odoo via `make addon wms_sap_connector`
- [x] 5.2 [Test] Buat test suite unit test otomatis `test_outbound_delivery_api.py` pada `addons/wms_sap_connector/tests/` untuk menguji skenario sukses pembuatan Delivery Order, idempotensi (`REQ-OUT-01`, `REQ-OUT-02`), dan pencatatan audit log (`REQ-OUT-03`)
- [x] 5.3 [Test] Jalankan seluruh test suite otomatis modul `wms_sap_connector` untuk memastikan integrasi berjalan bersih tanpa regresi

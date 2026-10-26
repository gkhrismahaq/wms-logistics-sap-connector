# Implementation Tasks: Extend Picking Dispatch Fields

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Tambahkan field `vehicle_id` (Many2one `wms.vehicle`) dan `driver_id` (Many2one `res.partner`) pada model `stock.picking` di `addons/wms_sap_connector/models/stock_picking.py`
- [x] 1.2 [Backend] Tambahkan field terkomputasi `total_weight` dan `total_volume` beserta method `_compute_total_weight_volume` pada model `stock.picking` di `addons/wms_sap_connector/models/stock_picking.py`

## 2. Security & Access Control
- [x] 2.1 [Security] Pastikan hak akses pembacaan dan penyuntingan field dispatch pada `stock.picking` dapat diakses oleh peran Logistics Dispatcher dan Warehouse Manager pada `addons/wms_sap_connector/security/ir.model.access.csv`

## 3. User Interface & Views
- [x] 3.1 [UI] Tambahkan group informasi armada dan pengantaran (`vehicle_id`, `driver_id`, `total_weight`, `total_volume`) pada form view `stock.view_picking_form` di `addons/wms_sap_connector/views/stock_picking_views.xml`
- [x] 3.2 [UI] Tambahkan kolom `vehicle_id` pada tree view `vpicktree_inherit_sap` di `addons/wms_sap_connector/views/stock_picking_views.xml`

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [Backend] Implementasikan method onchange `_onchange_vehicle_id` untuk mengisi `driver_id` secara otomatis dari `vehicle_id.driver_id` pada `addons/wms_sap_connector/models/stock_picking.py`
- [x] 4.2 [Backend] Implementasikan konstrain validasi kapasitas muatan `_check_vehicle_capacity` (`@api.constrains`) terhadap `max_weight` dan `max_volume` armada pada `addons/wms_sap_connector/models/stock_picking.py`

## 5. Verification & Testing
- [x] 5.1 [Test] Lakukan kompilasi sintaks Python dengan `python3 -m py_compile` pada seluruh file Python di `addons/wms_sap_connector/` dan upgrade modul Odoo via `make addon wms_sap_connector`
- [x] 5.2 [Test] Buat test suite unit test otomatis `test_picking_dispatch_fields.py` pada `addons/wms_sap_connector/tests/` untuk menguji penetapan armada & supir (`REQ-OUT-04`), onchange, komputasi berat/volume, dan validasi overcapacity (`REQ-OUT-05`)
- [x] 5.3 [Test] Jalankan seluruh test suite otomatis modul `wms_sap_connector` untuk memastikan seluruh skenario uji berhasil 100% tanpa regresi

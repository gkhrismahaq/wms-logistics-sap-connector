# Implementation Tasks: UI Backend Vehicle Views

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Verifikasi keberadaan dan kesiapan field model `wms.vehicle` (`license_plate`, `driver_id`, `max_weight`, `max_volume`, `state`) pada `addons/wms_sap_connector/models/wms_vehicle.py` untuk konsumsi view

## 2. Security & Access Control
- [x] 2.1 [Security] Verifikasi hak akses grup `group_wms_dispatcher`, `group_wms_manager`, dan `group_wms_operator` terhadap model `wms.vehicle` pada `addons/wms_sap_connector/security/ir.model.access.csv`

## 3. User Interface & Views
- [x] 3.1 [UI] Buat Tree View `view_wms_vehicle_tree` dengan widget badge dekoratif status pada `addons/wms_sap_connector/views/wms_vehicle_views.xml`
- [x] 3.2 [UI] Buat Form View `view_wms_vehicle_form` dengan statusbar widget dan pengelompokan informasi pengemudi serta kapasitas kargo pada `addons/wms_sap_connector/views/wms_vehicle_views.xml`
- [x] 3.3 [UI] Buat Search View `view_wms_vehicle_search` dengan filter cepat status dan pengelompokan group by pada `addons/wms_sap_connector/views/wms_vehicle_views.xml`
- [x] 3.4 [UI] Definisikan Window Action `action_wms_vehicle` dan susunan menu navigasi `menu_wms_logistics_root` serta `menu_wms_vehicle` pada `addons/wms_sap_connector/views/wms_vehicle_views.xml`
- [x] 3.5 [Backend] Daftarkan file `views/wms_vehicle_views.xml` ke dalam daftar data manifest modul pada `addons/wms_sap_connector/__manifest__.py`

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [UI] Verifikasi integrasi default filter dan pengurutan (*default order*) armada kendaraan pada action window di `addons/wms_sap_connector/views/wms_vehicle_views.xml`

## 5. Verification & Testing
- [x] 5.1 [Test] Lakukan validasi sintaks XML views dan upgrade modul Odoo via `make addon wms_sap_connector`
- [x] 5.2 [Test] Buat test suite unit test `test_vehicle_views.py` pada `addons/wms_sap_connector/tests/` untuk menguji pemuatan Tree, Form, Search view, dan Window Action `wms.vehicle` (`REQ-FLT-03`)
- [x] 5.3 [Test] Jalankan seluruh test suite otomatis modul `wms_sap_connector` untuk memastikan integrasi berjalan bersih tanpa regresi

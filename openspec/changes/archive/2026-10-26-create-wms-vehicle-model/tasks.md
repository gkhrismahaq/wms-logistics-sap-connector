# Implementation Tasks: Create WMS Vehicle Model

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Definisikan konstanta status operasional armada kendaraan (`VEHICLE_STATE_AVAILABLE`, `VEHICLE_STATE_ON_DELIVERY`, `VEHICLE_STATE_MAINTENANCE`, `VEHICLE_STATE_SELECTION`) pada `addons/wms_sap_connector/constants.py`
- [x] 1.2 [Backend] Implementasikan model data baru `wms.vehicle` dengan field `license_plate`, `driver_id`, `max_weight`, `max_volume`, dan `state` beserta `_rec_name = "license_plate"` pada `addons/wms_sap_connector/models/wms_vehicle.py`
- [x] 1.3 [Backend] Daftarkan impor modul model `wms_vehicle` ke dalam package models pada `addons/wms_sap_connector/models/__init__.py`

## 2. Security & Access Control
- [x] 2.1 [Security] Daftarkan hak akses keamanan model `wms.vehicle` untuk grup `group_wms_dispatcher` (CRUD), `group_wms_manager` (CRUD), `base.group_system` (CRUD), dan `group_wms_operator` (Read-only) pada `addons/wms_sap_connector/security/ir.model.access.csv`

## 3. User Interface & Views
- [x] 3.1 [UI] Verifikasi kesiapan deklarasi model `wms.vehicle` dan integritas file manifest `addons/wms_sap_connector/__manifest__.py` sebelum penyediaan antarmuka Tree/Form/Menu pada change `ui-backend-vehicle-views`

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [Backend] Menerapkan konstrain SQL keunikan nomor plat polisi `_sql_constraints = [('license_plate_unique', 'unique(license_plate)', ...)]` pada `addons/wms_sap_connector/models/wms_vehicle.py`
- [x] 4.2 [Backend] Menerapkan validasi ORM `@api.constrains('max_weight', 'max_volume')` untuk memastikan nilai kapasitas muatan non-negatif pada `addons/wms_sap_connector/models/wms_vehicle.py`

## 5. Verification & Testing
- [x] 5.1 [Test] Jalankan kompilasi sintaks Python dengan `python3 -m py_compile` pada seluruh file Python di `addons/wms_sap_connector/` dan lakukan upgrade modul Odoo via `make addon wms_sap_connector`
- [x] 5.2 [Test] Buat test suite unit test otomatis `test_wms_vehicle.py` pada `addons/wms_sap_connector/tests/` untuk menguji pembuatan record armada, SQL constraint keunikan plat nomor, dan validasi kapasitas non-negatif (`REQ-FLT-01`)
- [x] 5.3 [Test] Jalankan pengujian hak akses keamanan model `wms.vehicle` (`REQ-FLT-02`) untuk memastikan grup Dispatcher/Manager memiliki akses penuh dan Operator berstatus hanya-baca

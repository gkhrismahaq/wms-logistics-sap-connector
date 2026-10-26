# Implementation Tasks: Extend Warehouse Location Model

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Buat file model `addons/wms_sap_connector/models/stock_location.py` yang mewarisi `stock.location` dengan menambahkan bidang `sap_plant_code` (Char, `index=True`), `sap_sloc_code` (Char, `index=True`), dan memastikan `barcode` (Char, `index=True`, `copy=False`)
- [x] 1.2 [Backend] Daftarkan modul `stock_location` ke dalam file inisialisasi model `addons/wms_sap_connector/models/__init__.py`

## 2. Security & Access Control
- [x] 2.1 [Security] Verifikasi hak akses model `stock.location` pada grup sekuriti persediaan Odoo di mana staf gudang memiliki izin baca dan manajer gudang memiliki izin penuh pengelolaan konfigurasi SAP

## 3. User Interface & Views
- [x] 3.1 [UI] Buat file view `addons/wms_sap_connector/views/stock_location_views.xml` dengan mewarisi `stock.view_location_form` untuk menyematkan kelompok data `SAP Logistics Mapping` (`sap_plant_code`, `sap_sloc_code`, `barcode`)
- [x] 3.2 [UI] Warisi `stock.view_location_tree2` pada `addons/wms_sap_connector/views/stock_location_views.xml` untuk menampilkan kolom `sap_plant_code`, `sap_sloc_code`, dan `barcode`
- [x] 3.3 [Backend] Daftarkan file XML view `views/stock_location_views.xml` ke dalam daftar `data` pada manifest `addons/wms_sap_connector/__manifest__.py`

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [Backend] Verifikasi fungsionalitas pencarian record lokasi `stock.location` berdasarkan kriteria `sap_plant_code` dan `sap_sloc_code` melalui ORM Odoo
- [x] 4.2 [Integration] Validasi kesiapan pengindeksan database `index=True` dan perilaku `copy=False` pada field `barcode` untuk alur scanner staf gudang dan integrasi transaksi SAP

## 5. Verification & Testing
- [x] 5.1 [Test] Jalankan uji validasi sintaks Python pada `addons/wms_sap_connector/models/stock_location.py` dan validasi struktur XML pada `addons/wms_sap_connector/views/stock_location_views.xml`
- [x] 5.2 [Test] Lakukan upgrade modul via `make addon wms_sap_connector` dan verifikasi log kontainer Odoo bersih dari error/warning
- [x] 5.3 [Test] Lakukan pengujian fungsional skenario `REQ-MD-03` sesuai `openspec/changes/extend-warehouse-location-model/specs/master-data-models/spec.md` untuk verifikasi persistensi nilai, perilaku duplikasi barcode, dan pencarian lokasi SAP

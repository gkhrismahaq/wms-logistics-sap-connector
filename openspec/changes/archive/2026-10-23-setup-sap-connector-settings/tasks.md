# Implementation Tasks: Setup Sap Connector Settings

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Buat file `addons/wms_sap_connector/models/res_config_settings.py` dan definisikan model `ResConfigSettings` yang mewarisi `res.config.settings` dengan bidang `sap_base_url` dan `sap_api_token`
- [x] 1.2 [Backend] Daftarkan modul `res_config_settings` ke dalam file inisialisasi model `addons/wms_sap_connector/models/__init__.py`

## 2. Security & Access Control
- [x] 2.1 [Security] Verifikasi perlindungan akses model `res.config.settings` bawaan Odoo agar modifikasi parameter konfigurasi dibatasi untuk peran manajerial dan administrator sistem

## 3. User Interface & Views
- [x] 3.1 [UI] Buat file view `addons/wms_sap_connector/views/res_config_settings_views.xml` dengan mewarisi `stock.res_config_settings_view_form` dan menyematkan blok pengaturan SAP Integration Connector
- [x] 3.2 [UI] Terapkan konfigurasi masking password pada input field `sap_api_token` di `addons/wms_sap_connector/views/res_config_settings_views.xml`
- [x] 3.3 [Backend] Daftarkan file `views/res_config_settings_views.xml` ke dalam daftar `data` pada manifest `addons/wms_sap_connector/__manifest__.py`

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [Integration] Validasi persistensi penyimpanan parameter `sap_base_url` dan `sap_api_token` ke dalam tabel `ir.config_parameter` pada `addons/wms_sap_connector/models/res_config_settings.py`
- [x] 4.2 [Backend] Pastikan nilai parameter konfigurasi SAP dapat diakses oleh service backend secara aman menggunakan `get_param`

## 5. Verification & Testing
- [x] 5.1 [Test] Jalankan pengujian kompilasi sintaks Python pada `addons/wms_sap_connector/models/res_config_settings.py` dan validasi XML pada `addons/wms_sap_connector/views/res_config_settings_views.xml`
- [x] 5.2 [Test] Lakukan upgrade modul via `make addon wms_sap_connector` dan verifikasi log kontainer Odoo bersih dari error dependensi view
- [x] 5.3 [Test] Lakukan pengujian fungsional skenario `REQ-SETTING-01` sesuai spesifikasi pada `openspec/changes/setup-sap-connector-settings/specs/sap-connector-settings/spec.md` untuk verifikasi penyimpanan dan pembacaan parameter

# Implementation Tasks: Setup Wms Security Groups

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Verifikasi kesiapan definisi model `sap.sync.log` pada `addons/wms_sap_connector/models/sap_sync_log.py` untuk pemetaan hak akses ORM dan integrasi grup keamanan Odoo
- [x] 1.2 [Backend] Pastikan deklarasi dependensi modul inti (`base`, `stock`, `delivery`) pada manifest `addons/wms_sap_connector/__manifest__.py` tersedia untuk mendukung relasi grup internal pengguna

## 2. Security & Access Control
- [x] 2.1 [Security] Buat subdirektori `addons/wms_sap_connector/security` dan definisikan kategori modul `module_category_wms_logistics` serta tiga grup keamanan pengguna (`group_wms_operator`, `group_wms_dispatcher`, `group_wms_manager`) pada `addons/wms_sap_connector/security/security.xml`
- [x] 2.2 [Security] Konfigurasikan tabel Access Control List pada `addons/wms_sap_connector/security/ir.model.access.csv` guna memetakan izin CRUD model `sap.sync.log` untuk `group_wms_manager`, `group_wms_operator`, `group_wms_dispatcher`, dan `base.group_system`
- [x] 2.3 [Backend] Daftarkan file `security/security.xml` dan `security/ir.model.access.csv` secara berurutan ke dalam daftar `data` pada manifest `addons/wms_sap_connector/__manifest__.py`

## 3. User Interface & Views
- [x] 3.1 [UI] Verifikasi integrasi kategori keamanan modul WMS Logistics pada form manajemen pengguna Odoo melalui konfigurasi manifest di `addons/wms_sap_connector/__manifest__.py`

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [Security] Validasi penegakan hak akses pada level eksekusi method `action_retry_sync()` di `addons/wms_sap_connector/models/sap_sync_log.py` agar aksi terbatas bagi peran berwenang
- [x] 4.2 [Integration] Pastikan aturan hak akses model `sap.sync.log` tidak menghambat proses pencatatan otomatis transaksi inbound/outbound integrasi SAP pada `addons/wms_sap_connector/models/sap_sync_log.py`

## 5. Verification & Testing
- [x] 5.1 [Test] Jalankan pemeriksaan integritas struktur sintaks file XML dan format CSV pada `addons/wms_sap_connector/security/` untuk memastikan tidak ada kesalahan parse
- [x] 5.2 [Test] Lakukan upgrade modul dengan menjalankan `make addon wms_sap_connector` dan verifikasi log kontainer bersih dari pesan galat dependensi ID eksternal
- [x] 5.3 [Test] Lakukan pengujian fungsional skenario `REQ-AUDIT-03` sesuai spesifikasi pada `openspec/changes/setup-wms-security-groups/specs/integration-audit-log/spec.md` untuk mengonfirmasi pemisahan hak akses Warehouse Manager, Operator, Dispatcher, dan penolakan pengguna tanpa grup

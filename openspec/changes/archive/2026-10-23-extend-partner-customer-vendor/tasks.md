# Implementation Tasks: Extend Partner Customer Vendor

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Buat file model `addons/wms_sap_connector/models/res_partner.py` yang mewarisi `res.partner` dengan menambahkan bidang `sap_partner_code` (Char, `index=True`, `copy=False`)
- [x] 1.2 [Backend] Daftarkan modul `res_partner` ke dalam file inisialisasi model `addons/wms_sap_connector/models/__init__.py`

## 2. Security & Access Control
- [x] 2.1 [Security] Verifikasi hak akses model `res.partner` pada grup sekuriti WMS di mana pengguna internal memiliki izin baca dan modifikasi dibatasi untuk administrator serta manajer logistik

## 3. User Interface & Views
- [x] 3.1 [UI] Buat file view `addons/wms_sap_connector/views/res_partner_views.xml` dengan mewarisi `base.view_partner_form` untuk menyematkan bidang `sap_partner_code` di bawah `vat`
- [x] 3.2 [Backend] Daftarkan file XML view `views/res_partner_views.xml` ke dalam daftar `data` pada manifest `addons/wms_sap_connector/__manifest__.py`

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [Backend] Verifikasi fungsionalitas pencarian record kontak `res.partner` berdasarkan atribut `sap_partner_code` melalui ORM Odoo
- [x] 4.2 [Integration] Validasi kesiapan pengindeksan basis data `index=True` dan perilaku `copy=False` pada field `sap_partner_code` untuk mendukung idempotensi sinkronisasi rekanan SAP

## 5. Verification & Testing
- [x] 5.1 [Test] Jalankan uji kompilasi sintaks Python pada `addons/wms_sap_connector/models/res_partner.py` dan validasi struktur XML pada `addons/wms_sap_connector/views/res_partner_views.xml`
- [x] 5.2 [Test] Lakukan upgrade modul via `make addon wms_sap_connector` dan verifikasi log kontainer Odoo bersih dari error dependensi view
- [x] 5.3 [Test] Lakukan pengujian fungsional skenario `REQ-MD-02` sesuai `openspec/changes/extend-partner-customer-vendor/specs/master-data-models/spec.md` untuk verifikasi persistensi nilai, perilaku duplikasi, dan pencarian rekanan

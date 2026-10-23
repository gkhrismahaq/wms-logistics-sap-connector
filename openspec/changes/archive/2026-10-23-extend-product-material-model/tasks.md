# Implementation Tasks: Extend Product Material Model

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Buat file model `addons/wms_sap_connector/models/product_template.py` yang mewarisi `product.template` dengan menambahkan bidang `sap_material_code` (Char, `index=True`, `copy=False`)
- [x] 1.2 [Backend] Daftarkan modul `product_template` ke dalam file inisialisasi model `addons/wms_sap_connector/models/__init__.py`

## 2. Security & Access Control
- [x] 2.1 [Security] Verifikasi hak akses model `product.template` pada grup sekuriti WMS di mana staf operasional gudang memiliki izin baca dan manajer gudang memiliki izin modifikasi penuh

## 3. User Interface & Views
- [x] 3.1 [UI] Buat file view `addons/wms_sap_connector/views/product_template_views.xml` dengan mewarisi `product.product_template_only_form_view` untuk menampilkan bidang `sap_material_code` di bawah `barcode`
- [x] 3.2 [UI] Pastikan penyajian widget foto produk `image_1920` dan atribut logistik `weight` serta `volume` tersaji secara konsisten pada antarmuka formulir produk
- [x] 3.3 [Backend] Daftarkan file XML view `views/product_template_views.xml` ke dalam daftar `data` pada manifest `addons/wms_sap_connector/__manifest__.py`

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [Backend] Verifikasi ketersediaan dan delegasi atribut `sap_material_code` dari `product.template` ke model varian `product.product` melalui mekanisme bawaan Odoo
- [x] 4.2 [Integration] Validasi kesiapan pengindeksan basis data `index=True` dan perilaku `copy=False` pada field `sap_material_code` untuk mendukung idempotensi sinkronisasi SAP

## 5. Verification & Testing
- [x] 5.1 [Test] Jalankan uji kompilasi sintaks Python pada `addons/wms_sap_connector/models/product_template.py` dan validasi struktur XML pada `addons/wms_sap_connector/views/product_template_views.xml`
- [x] 5.2 [Test] Lakukan upgrade modul via `make addon wms_sap_connector` dan verifikasi log kontainer Odoo bersih dari error dependensi view
- [x] 5.3 [Test] Lakukan pengujian fungsional skenario `REQ-MD-01` sesuai `openspec/changes/extend-product-material-model/specs/master-data-models/spec.md` untuk verifikasi penyimpanan nilai, perilaku duplikasi, dan visibilitas data

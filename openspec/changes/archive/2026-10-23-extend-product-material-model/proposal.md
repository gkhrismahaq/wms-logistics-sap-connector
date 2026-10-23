# Proposal: Extend Product Material Model

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | extend-product-material-model                 |
| **Roadmap Phase**  | Fase 2: Perluasan Master Data & Sinkronisasi (Master Data) |
| **Target Cap.**    | `master-data-models`                          |
| **Est. Effort**    | 3 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Dalam arsitektur Two-Tier ERP, sistem SAP bertindak sebagai Upper Line yang mengelola kode penomoran material terpusat (SKU/Item Master), sedangkan Odoo 17 berfungsi sebagai sistem eksekusi WMS dan logistik di lantai gudang. Agar produk di Odoo dapat dipetakan secara akurat dan konsisten dengan data material dari SAP, model `product.template` perlu diperluas dengan field kode material SAP (`sap_material_code`). Selain itu, atribut fisik produk seperti berat (`weight`) dan volume (`volume`) serta visualisasi gambar produk (`image_1920`) perlu disajikan secara ergonomis pada antarmuka Form Produk untuk memfasilitasi verifikasi visual oleh staf gudang (picker/packer) saat proses penerimaan maupun pengeluaran barang.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 2 (Kapabilitas 2.1).

## What Changes
Perubahan mencakup penambahan atribut kode SAP pada model produk, penyajian field pada antarmuka Form Odoo, serta penyiapan indeks database untuk kebutuhan integrasi master data:
- **Backend (ORM & Models):** Mewarisi model `product.template` pada file `addons/wms_sap_connector/models/product_template.py` dengan menambahkan bidang `sap_material_code` (Char, `index=True`, `copy=False`). Memanfaatkan field kargo bawaan Odoo (`weight`, `volume`, dan `image_1920`) agar siap digunakan pada proses verifikasi gudang dan sinkronisasi SAP.
- **Security & Access Rights:** Mewarisi aturan hak akses standar Odoo untuk model `product.template`. Hak modifikasi dibatasi untuk Administrator dan Manajer Gudang (`stock.group_stock_manager`), sementara Staf Gudang / Picker (`stock.group_stock_user`) memiliki hak baca untuk verifikasi SKU dan gambar produk.
- **Views & UI:** Mewarisi Form View `product.product_template_only_form_view` pada `addons/wms_sap_connector/views/product_template_views.xml` untuk menyematkan bidang `sap_material_code` pada halaman utama produk secara rapi bersama informasi standar Odoo.
- **Integration & API:** Field `sap_material_code` dikonfigurasi dengan indeks pencarian unik/cepat sebagai landasan rekonsiliasi data dan pencegahan duplikasi (*idempotency*) bagi endpoint penerima master data SAP di masa mendatang.

## Capabilities
### New Capabilities
- `master-data-models`: Perluasan model data standar Odoo untuk menampung atribut kode referensi SAP dan spesifikasi kargo.

### Modified Capabilities
- `None`

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/models/product_template.py`
  - `addons/wms_sap_connector/views/product_template_views.xml`
- **Files to Modify:**
  - `addons/wms_sap_connector/models/__init__.py`
  - `addons/wms_sap_connector/__manifest__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 3.2)
  - `docs/roadmap.md` (Kapabilitas 2.1)
- **Estimated Effort:** 3 jam.
- **Complexity & Risk Analysis:** Kompleksitas dan risiko rendah (Low). Implementasi murni menggunakan mekanisme pewarisan ORM (`_inherit = 'product.template'`) yang non-destruktif dan kompatibel penuh dengan modul standar Odoo. Pengaturan `copy=False` menjamin kode material SAP tidak terduplikasi saat record produk diduplikasi secara manual.

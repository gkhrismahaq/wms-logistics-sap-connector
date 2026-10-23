# Design Document: Extend Product Material Model

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | extend-product-material-model                 |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `product.template`, `product.product`         |

## Context
Sistem WMS Odoo 17 mengintegrasikan proses operasional pergudangan dengan sistem ERP pusat SAP. Modul `wms_sap_connector` telah memiliki infrastruktur dasar (Fase 1) meliputi tabel audit log transaksi `sap.sync.log` dan pengaturan konfigurasi `res.config.settings`. Memasuki Fase 2 (Master Data), integrasi membutuhkan pemetaan SKU master material antara SAP dan Odoo. Odoo secara bawaan menyediakan model `product.template` (dan varian `product.product`) yang telah dilengkapi field `weight`, `volume`, dan `image_1920` (melalui dependensi `stock` dan `delivery`). Namun, atribut identifikasi kode material unik dari SAP (`sap_material_code`) belum tersedia.

## Goals / Non-Goals
### Goals
- Memperluas model `product.template` dengan menambahkan bidang `sap_material_code` (Char, `index=True`, `copy=False`) melalui inheritance ORM Odoo 17 yang bersih dan terisolasi pada `addons/wms_sap_connector/models/product_template.py`.
- Mewarisi Form View `product.product_template_only_form_view` pada `addons/wms_sap_connector/views/product_template_views.xml` untuk menampilkan bidang `sap_material_code` di bawah `default_code` / `barcode`.
- Memastikan atribut fisik kargo (`weight`, `volume`) dan widget visual produk (`image_1920`) dapat diakses secara ergonomis oleh staf gudang saat pemeriksaan fisik produk.
- Menjamin pencegahan duplikasi kode secara tidak sengaja saat record diduplikasi melalui parameter `copy=False`.

### Non-Goals
- Tidak mengimplementasikan endpoint REST API penerima sinkronisasi master data (hal ini menjadi ruang lingkup perubahan berikutnya pada `api-receive-sap-master-data` di Kapabilitas 2.2).
- Tidak membuat model data master terpisah khusus material karena `product.template` Odoo sudah memiliki kapabilitas manajemen stok yang lengkap.
- Tidak memperluas model rekanan (`res.partner`) atau lokasi gudang (`stock.location`) pada change ini.

## Decisions (ADR)
### 1. Pewarisan Model product.template Melalui _inherit Bawaan Odoo
- **Rationale:** Menggunakan `_inherit = 'product.template'` memungkinkan produk SAP terintegrasi langsung secara natif dengan seluruh proses pergudangan standar Odoo 17 (penerimaan barang, pemindahan internal, pengemasan, dan pengiriman). Selain itu, varian produk `product.product` secara otomatis mewarisi field ini melalui mekanisme `_inherits`.
- **Alternatives Considered:** Membuat tabel model mandiri `sap.material.master`. Opsi ini ditolak karena menimbulkan duplikasi data dan membutuhkan logika sinkronisasi internal tambahan yang kompleks serta rawan desinkronisasi terhadap inventori Odoo.
- **Consequences:** Field `sap_material_code` tersimpan langsung pada tabel basis data `product_template` dan siap digunakan di seluruh ekosistem Odoo.

### 2. Penerapan Pengindeksan Basis Data (index=True) dan Pencegahan Duplikasi (copy=False)
- **Rationale:** Saat integrasi menerima dokumen transaksi seperti Purchase Order (`sap_doc_number`) atau instruksi pengiriman dari SAP, sistem akan melakukan lookup SKU menggunakan `sap_material_code`. Indeks database B-Tree memastikan waktu pencarian data tetap konstan $O(\log n)$ meskipun data material mencapai ratusan ribu baris. Parameter `copy=False` menjamin saat pengguna menduplikasi produk di antarmuka web, kode unik SAP tidak ikut terduplikasi.
- **Alternatives Considered:** Menggunakan SQL Unique Constraint langsung pada level basis data. Opsi ini dihindari pada tahap ini agar tidak menimbulkan galat pada produk-produk internal gudang atau aset pendukung yang tidak memiliki kode SAP (`NULL` / `False`).
- **Consequences:** Sedikit penambahan overhead saat operasi penulisan (*insert*), namun memberikan performa pencarian yang optimal pada proses sinkronisasi API.

### 3. Pewarisan View product.product_template_only_form_view
- **Rationale:** Form view `product.product_template_only_form_view` adalah view standar utama yang digunakan pengguna saat mengelola katalog produk di modul Inventory Odoo 17. Menempatkan `sap_material_code` di samping field identifikasi internal (`default_code` / `barcode`) menyajikan konteks data yang padu bagi pengguna.
- **Alternatives Considered:** Menambahkan notebook tab baru khusus integrasi SAP. Pendekatan ini dinilai berlebihan (*over-engineered*) karena saat ini hanya menambahkan satu field atribut penomoran material.
- **Consequences:** Layout form tetap ringkas, intuitif, dan tidak mengubah kebiasaan operator gudang.

## Technical Architecture & Data Schema
### Model Inheritance Python
```python
# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    sap_material_code = fields.Char(
        string="SAP Material Code",
        index=True,
        copy=False,
        help="Unique SKU identifier in SAP system",
    )
```

### View Inheritance XML
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="product_template_form_view_inherit_sap" model="ir.ui.view">
        <field name="name">product.template.form.inherit.sap</field>
        <field name="model">product.template</field>
        <field name="inherit_id" ref="product.product_template_only_form_view"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='barcode']" position="after">
                <field name="sap_material_code" placeholder="e.g. MAT-KOPI-01"/>
            </xpath>
        </field>
    </record>
</odoo>
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Konflik nama field dengan modul pihak ketiga lainnya | Low | Menggunakan prefiks spesifik arsitektur `sap_material_code` yang representatif dan tidak ambigu. |
| Duplikasi kode material SAP jika pengguna mengisi kode yang sama secara manual | Medium | Terapkan parameter `copy=False` pada field ORM dan siapkan validasi rekonsiliasi pada controller integrasi master data (Kapabilitas 2.2). |
| Keterlambatan rendering form akibat ukuran file gambar besar | Low | Memanfaatkan widget bawaan Odoo `image_1920` yang secara otomatis mengelola varian thumbnail terkompresi (`image_128`, `image_256`, `image_1024`) melalui `image.mixin`. |

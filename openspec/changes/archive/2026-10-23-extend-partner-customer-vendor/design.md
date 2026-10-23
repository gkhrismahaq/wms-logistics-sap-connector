# Design Document: Extend Partner Customer Vendor

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | extend-partner-customer-vendor                |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `res.partner`                                 |

## Context
Dalam ekosistem pergudangan dan logistik Two-Tier ERP, data rekanan bisnis (Vendor/Pemasok dan Customer/Pelanggan) merupakan entitas penting pada proses penerimaan barang (Inbound Goods Receipt dari vendor) dan pengiriman barang (Outbound Delivery ke pelanggan). Sistem SAP bertindak sebagai Master Record yang merekam kode rekanan unik seperti `VEND-INDOMARCO` dan `CUST-ALFAMART-01`. Model `res.partner` bawaan Odoo 17 telah memiliki field referensi internal (`ref`), namun belum memiliki atribut identifikasi kode SAP (`sap_partner_code`) yang terindeks secara independen guna mencegah tabrakan data dengan referensi internal lokal Odoo.

## Goals / Non-Goals
### Goals
- Memperluas model `res.partner` dengan menambahkan bidang `sap_partner_code` (Char, `index=True`, `copy=False`) melalui inheritance ORM Odoo 17 pada file `addons/wms_sap_connector/models/res_partner.py`.
- Mewarisi Form View kontak `base.view_partner_form` pada `addons/wms_sap_connector/views/res_partner_views.xml` untuk menyematkan bidang `sap_partner_code` di bawah field `vat`.
- Menyiapkan indeks basis data B-Tree pada PostgreSQL untuk pencarian cepat $O(\log n)$ saat validasi transaksi payload API SAP.
- Menjamin pencegahan duplikasi kode saat record mitra diduplikasi melalui parameter `copy=False`.

### Non-Goals
- Tidak mengimplementasikan controller atau endpoint REST API sinkronisasi master data rekanan (hal ini merupakan ruang lingkup change `api-receive-sap-master-data` pada Kapabilitas 2.2).
- Tidak membuat tabel model mitra terpisah karena Odoo telah memiliki `res.partner` yang terintegrasi secara komprehensif di seluruh modul.
- Tidak mengubah aturan relasi hierarki kontak atau modul akuntansi di luar lingkup integrasi WMS.

## Decisions (ADR)
### 1. Pewarisan Model res.partner Melalui _inherit Bawaan Odoo
- **Rationale:** Menggunakan `_inherit = 'res.partner'` memungkinkan seluruh transaksi logistik Odoo (Picking, Surat Jalan, Delivery Order) secara langsung mengenali dan mereferensikan rekanan SAP tanpa perlu tabel perantara.
- **Alternatives Considered:** Membuat tabel model mandiri `sap.partner.master`. Pendekatan ini ditolak karena memicu fragmentasi data rekanan, memerlukan sinkronisasi internal ganda yang rentan inkonsistensi, dan merusak integrasi standar dengan modul `stock` maupun `delivery`.
- **Consequences:** Field `sap_partner_code` tersimpan langsung pada tabel `res_partner` di PostgreSQL dan dapat diakses dengan mudah oleh seluruh ORM query.

### 2. Penggunaan Field Eksklusif sap_partner_code Dibandingkan Field ref Bawaan Odoo
- **Rationale:** Field `ref` bawaan Odoo sering dimanfaatkan oleh pengguna atau modul lain untuk nomor referensi lokal internal. Menggunakan field khusus `sap_partner_code` menjamin isolasi data master SAP sehingga tidak akan tertimpa atau terhapus oleh perubahan operasional manual di Odoo.
- **Alternatives Considered:** Menggunakan kembali field `ref` untuk menyimpan kode SAP. Opsi ini ditolak karena menimbulkan ambiguitas semantik dan risiko tinggi tertimpa data manual pengguna.
- **Consequences:** Struktur data integrasi menjadi tegas, eksplisit, dan aman untuk automasi sinkronisasi API.

### 3. Penyematan Field pada Form View Kontak di Bawah Field vat (Tax ID)
- **Rationale:** Field `vat` terletak pada panel informasi utama profil kontak di `base.view_partner_form`. Menempatkan `sap_partner_code` di area tersebut memberikan keterbacaan yang ergonomis dan selaras dengan atribut identifikasi legal perusahaan.
- **Alternatives Considered:** Membuat tab baru khusus integrasi SAP. Pendekatan ini dinilai berlebihan (*over-engineered*) untuk penambahan satu field identifikasi.
- **Consequences:** Antarmuka formulir kontak tetap ringkas, bersih, dan tidak mengganggu tata letak visual bawaan Odoo.

## Technical Architecture & Data Schema
### Model Inheritance Python
```python
# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    sap_partner_code = fields.Char(
        string="SAP Partner Code",
        index=True,
        copy=False,
        help="Unique Partner/Vendor/Customer identifier in SAP system",
    )
```

### View Inheritance XML
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_partner_form_inherit_sap" model="ir.ui.view">
        <field name="name">res.partner.form.inherit.sap</field>
        <field name="model">res.partner</field>
        <field name="inherit_id" ref="base.view_partner_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='vat']" position="after">
                <field name="sap_partner_code" placeholder="e.g. VEND-INDOMARCO or CUST-ALFAMART-01"/>
            </xpath>
        </field>
    </record>
</odoo>
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Konflik nama field dengan modul pihak ketiga | Low | Menggunakan penamaan spesifik `sap_partner_code` dengan prefiks modul. |
| Duplikasi kode mitra jika dibuat secara manual | Medium | Menerapkan `copy=False` pada field ORM dan menerapkan validasi idempotensi pada controller integrasi master data (Kapabilitas 2.2). |
| Penurunan performa saat query kontak SAP skala besar | Low | Memastikan atribut `index=True` dikonfigurasi sehingga PostgreSQL otomatis membangun indeks B-Tree. |

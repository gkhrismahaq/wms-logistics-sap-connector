# Design Document: Extend Warehouse Location Model

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | extend-warehouse-location-model               |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `stock.location`                              |

## Context
Dalam arsitektur Two-Tier ERP, SAP mengelola struktur inventori tingkat atas menggunakan entitas Plant (pabrik atau unit operasional logistik) dan Storage Location (SLoc / gudang penyimpanan barang). Sementara itu, Odoo 17 WMS mengelola hierarki lokasi fisik yang jauh lebih mendalam dan fleksibel, mulai dari gudang (Warehouse), zona penyimpanan (Internal Location), hingga nomor lorong, rak, dan bin penempatan barang (*putaway bin*).

Untuk menghubungkan kedua dunia ini tanpa mendisrupsi logika stok standar Odoo, entitas `stock.location` pada Odoo perlu diperluas agar mampu merekam kode Plant SAP (`sap_plant_code`) dan kode Storage Location SAP (`sap_sloc_code`). Selain itu, guna mendukung efisiensi operasional petugas gudang yang menggunakan pemindai barcode portabel (*barcode scanner*), setiap lokasi rak fisik wajib memiliki representasi barcode unik (`barcode`) yang terindeks secara optimal di database.

## Goals / Non-Goals
### Goals
- Memperluas model `stock.location` dengan field `sap_plant_code` (Char, `index=True`), `sap_sloc_code` (Char, `index=True`), dan memastikan `barcode` (Char, `index=True`, `copy=False`) melalui inheritance ORM Odoo 17 pada `addons/wms_sap_connector/models/stock_location.py`.
- Mewarisi Form View `stock.view_location_form` pada `addons/wms_sap_connector/views/stock_location_views.xml` untuk menyajikan kelompok data "SAP Logistics Mapping" yang berisi konfigurasi Plant, SLoc, dan Barcode.
- Mewarisi Tree View `stock.view_location_tree2` dengan menyematkan kolom `sap_plant_code`, `sap_sloc_code`, dan `barcode` (opsional terlihat) guna mempermudah audit lokasi oleh Kepala Gudang.
- Mengonfigurasi indeks basis data B-Tree pada PostgreSQL untuk menjamin kecepatan kueri pencarian saat alur penempatan barang (*putaway*) atau penerimaan barang (*Goods Receipt*) dari SAP.

### Non-Goals
- Tidak mengimplementasikan alur algoritma *Putaway Rule* otomatis pada change ini (hal ini merupakan ruang lingkup change `automate-putaway-bin-allocation` pada Kapabilitas 3.1).
- Tidak mengimplementasikan endpoint REST API sinkronisasi master data lokasi dari SAP (hal ini ditangani pada change `api-receive-sap-master-data` pada Kapabilitas 2.2).
- Tidak mengubah logika kalkulasi kuantitas stok barang bawaan tabel `stock_quant` Odoo.

## Decisions (ADR)
### 1. Pewarisan Model stock.location Menggunakan ORM _inherit Bawaan Odoo
- **Rationale:** Menggunakan mekanisme `_inherit = 'stock.location'` menjamin kompatibilitas menyeluruh dengan modul persediaan Odoo (`stock`), rute perpindahan (*stock rules*), dan dokumen transfer (`stock.picking`).
- **Alternatives Considered:** Membuat model tabel terpisah seperti `sap.location.mapping`. Opsi ini ditolak karena memerlukan query JOIN berulang pada setiap transaksi pergudangan dan memperumit pemeliharaan data lokasi.
- **Consequences:** Atribut kode Plant, SLoc, dan Barcode terintegrasi langsung pada tabel `stock_location` dan dapat langsung diakses oleh ORM tanpa overhead query tambahan.

### 2. Standarisasi dan Isolasi Field sap_plant_code dan sap_sloc_code
- **Rationale:** SAP membedakan unit bisnis secara ketat melalui 4-karakter kode Plant (misal `1000`) dan 4-karakter kode SLoc (misal `SL01` atau `1001`). Menyimpan kedua entitas ini ke dalam field terpisah yang terindeks menjamin presisi pemetaan dokumen SAP saat data PO atau Delivery Order tiba di WMS.
- **Alternatives Considered:** Menggabungkan kode Plant dan SLoc menjadi satu field gabungan string (misal `1000/SL01`). Pendekatan ini ditolak karena menyulitkan proses kueri relasional dan filtering data per Plant.
- **Consequences:** Pengelolaan data lebih terstruktur dan mempermudah validasi payload transaksi SAP pada modul integrasi API.

### 3. Penegasan Atribut copy=False pada Barcode Lokasi Fisik
- **Rationale:** Barcode rak fisik di gudang merepresentasikan label unik yang ditempel pada fisik lorong/rak. Jika pengguna menduplikasi data lokasi di antarmuka Odoo, nilai `barcode` tidak boleh ikut tersalin agar tidak terjadi konflik pemindaian scanner di lapangan.
- **Alternatives Considered:** Mengizinkan duplikasi barcode atau bergantung pada peringatan manual pengguna. Opsi ini ditolak karena risiko tinggi tabrakan scan barcode oleh operator gudang.
- **Consequences:** Ketika record lokasi diduplikasi, field `barcode` akan secara otomatis dikosongkan oleh ORM Odoo.

## Technical Architecture & Data Schema
### Model Inheritance Python
File target: `addons/wms_sap_connector/models/stock_location.py`
```python
# -*- coding: utf-8 -*-
from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    sap_plant_code = fields.Char(
        string="SAP Plant Code",
        size=4,
        index=True,
        help="SAP Plant / Facility code governing this storage facility (e.g. 1000)",
    )
    sap_sloc_code = fields.Char(
        string="SAP Storage Location",
        size=4,
        index=True,
        help="SAP Storage Location code (e.g. SL01, 1001)",
    )
    barcode = fields.Char(
        string="Barcode",
        index=True,
        copy=False,
        help="Physical barcode attached to the aisle, rack, or bin for scanner operations",
    )
```

### View Inheritance XML
File target: `addons/wms_sap_connector/views/stock_location_views.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Inherit Form View -->
    <record id="view_location_form_inherit_sap" model="ir.ui.view">
        <field name="name">stock.location.form.inherit.sap</field>
        <field name="model">stock.location</field>
        <field name="inherit_id" ref="stock.view_location_form"/>
        <field name="arch" type="xml">
            <xpath expr="//group[@name='additional_info']" position="after">
                <group string="SAP Logistics Mapping" name="sap_logistics_mapping">
                    <group>
                        <field name="sap_plant_code" placeholder="e.g. 1000"/>
                        <field name="sap_sloc_code" placeholder="e.g. SL01 or 1001"/>
                    </group>
                    <group>
                        <field name="barcode" placeholder="e.g. LOC-BIN-A01"/>
                    </group>
                </group>
            </xpath>
        </field>
    </record>

    <!-- Inherit Tree View -->
    <record id="view_location_tree2_inherit_sap" model="ir.ui.view">
        <field name="name">stock.location.tree.inherit.sap</field>
        <field name="model">stock.location</field>
        <field name="inherit_id" ref="stock.view_location_tree2"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='usage']" position="after">
                <field name="sap_plant_code" optional="show"/>
                <field name="sap_sloc_code" optional="show"/>
                <field name="barcode" optional="show"/>
            </xpath>
        </field>
    </record>
</odoo>
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Duplikasi barcode fisik rak antar lokasi gudang | Medium | Menerapkan `copy=False` pada ORM dan menyediakan indeks pencarian untuk mendeteksi kesamaan barcode. |
| Perbedaan penamaan struktur lokasi fisik Odoo vs SAP SLoc | Low | Menjelaskan panduan pemetaan di mana satu SAP SLoc dapat menaungi banyak subdivisi lokasi rak/bin di Odoo. |
| Beban komputasi kueri lokasi pada sistem gudang skala besar | Low | Memastikan kolom `sap_plant_code`, `sap_sloc_code`, dan `barcode` memiliki indeks B-Tree aktif (`index=True`). |

# Design Document: UI Backend Vehicle Views

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | ui-backend-vehicle-views                      |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `wms.vehicle`                                 |

## Context
Model data `wms.vehicle` telah didefinisikan pada backend Odoo dengan atribut nomor plat (`license_plate`), supir penanggung jawab (`driver_id`), batas muatan berat (`max_weight`), volume kubikasi (`max_volume`), dan status operasional (`state`). Sesuai dengan roadmap proyek ([roadmap.md](../../docs/roadmap.md) — Fase 4, Kapabilitas 4.1) dan acuan teknis ([tsd.md](../../docs/tsd.md) — Bagian 3.2), tahapan ini melengkapi backend data dengan antarmuka grafis Odoo 17 (Tree view, Form view, Search view, Window Action, dan Menu Navigasi).

## Goals / Non-Goals
### Goals
- Menyusun file antarmuka `views/wms_vehicle_views.xml` dengan komponen XML Odoo 17 standar.
- Menyediakan Tree view (`view_wms_vehicle_tree`) dengan widget badge status berwarna semantik (`decoration-success` untuk `available`, `decoration-info` untuk `on_delivery`, `decoration-warning` untuk `maintenance`).
- Menyediakan Form view (`view_wms_vehicle_form`) dengan statusbar interaktif dan pengelompokan grid 2 kolom (informasi supir & spesifikasi kapasitas muatan).
- Menyediakan Search view (`view_wms_vehicle_search`) dengan pencarian teks, filter cepat status operasional, dan pengelompokan data (*Group By*).
- Menghubungkan tampilan melalui Window Action (`action_wms_vehicle`).
- Menyediakan struktur menu navigasi terpusat: menu induk "Logistics & Delivery" (`menu_wms_logistics_root`) di bawah `stock.menu_stock_root` dan submenu "Fleet Vehicles" (`menu_wms_vehicle`).
- Mendaftarkan file XML views pada manifest `addons/wms_sap_connector/__manifest__.py`.
- Menyediakan automated unit test untuk memvalidasi integritas arsitektur view dan ketersediaan menu.

### Non-Goals
- Tidak menambahkan field relasi baru pada dokumen pengiriman `stock.picking` (akan dikerjakan pada change `extend-picking-dispatch-fields`).
- Tidak mengimplementasikan tampilan laporan cetak Surat Jalan PDF (merupakan lingkup change `report-official-surat-jalan`).
- Tidak membuat antarmuka portal publik atau aplikasi seluler supir pada change ini.

## Decisions (ADR)
### 1. Pembentukan Menu Induk "Logistics & Delivery" di Bawah Menu Utama Inventori
- **Rationale:** Pada alur logistik Two-Tier WMS, aktivitas dispatching armada, penerbitan surat jalan, dan monitoring pengiriman merupakan perpanjangan alami dari manajemen inventori gudang. Membuat menu induk `menu_wms_logistics_root` dengan urutan `sequence="25"` di bawah `stock.menu_stock_root` (berada di antara Operasi Transfer dan Konfigurasi) menyediakan ruang navigasi terpadu bagi seluruh fitur Fase 4 (manajemen armada, dispatching, surat jalan, dan POD).
- **Alternatives Considered:** Menempatkan menu armada di bawah menu `stock.menu_stock_config_settings` (Konfigurasi). Alternatif ini ditolak karena data armada merupakan data operasional aktif harian yang dipantau oleh dispatcher, bukan sekadar setting sistem statis.
- **Consequences:** Struktur navigasi Odoo tetap tertata rapi, ramah pengguna bagi staf dispatcher, dan siap menampung submenu logistik di fase berikutnya.

### 2. Pemanfaatan Badge Status pada Tree View dan Statusbar pada Form View
- **Rationale:** Status armada (`available`, `on_delivery`, `maintenance`) adalah indikator operasional utama sebelum dispatcher mengalokasikan pesanan pengiriman. Menampilkan widget badge status dengan warna semantik di Tree view mempercepat identifikasi truk yang siap jalan, sedangkan statusbar di Form view menyajikan status proses yang interaktif.
- **Alternatives Considered:** Menampilkan field status hanya sebagai teks standar tanpa styling badge. Alternatif ini ditolak karena memperlambat efisiensi pembacaan data oleh dispatcher.
- **Consequences:** Pengalaman pengguna (UX) selaras dengan standar desain Odoo 17 enterprise.

### 3. Pemisahan Terisolasi File XML Views (`wms_vehicle_views.xml`)
- **Rationale:** Mematuhi prinsip Clean Architecture dan modularitas. Memisahkan antarmuka armada ke dalam `views/wms_vehicle_views.xml` menjaga isolasi domain visual, mempermudah pelacakan git diff, dan mencegah file `stock_picking_views.xml` membengkak (*bloating*).
- **Alternatives Considered:** Menggabungkan deklarasi XML armada ke dalam `stock_picking_views.xml`. Alternatif ini ditolak karena melanggar prinsip *Single Responsibility*.
- **Consequences:** Modul tetap bersih, terstruktur rapi, dan mudah dipelihara.

## Technical Architecture & Data Schema

### 1. Struktur XML Antarmuka Armada (`views/wms_vehicle_views.xml`)
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Tree View -->
    <record id="view_wms_vehicle_tree" model="ir.ui.view">
        <field name="name">wms.vehicle.tree</field>
        <field name="model">wms.vehicle</field>
        <field name="arch" type="xml">
            <tree string="Fleet Vehicles">
                <field name="license_plate"/>
                <field name="driver_id"/>
                <field name="max_weight" string="Max Weight (kg)"/>
                <field name="max_volume" string="Max Volume (m³)"/>
                <field name="state" widget="badge"
                       decoration-success="state == 'available'"
                       decoration-info="state == 'on_delivery'"
                       decoration-warning="state == 'maintenance'"/>
            </tree>
        </field>
    </record>

    <!-- Form View -->
    <record id="view_wms_vehicle_form" model="ir.ui.view">
        <field name="name">wms.vehicle.form</field>
        <field name="model">wms.vehicle</field>
        <field name="arch" type="xml">
            <form string="Fleet Vehicle">
                <header>
                    <field name="state" widget="statusbar" statusbar_visible="available,on_delivery,maintenance"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <label for="license_plate" class="oe_edit_only" string="License Plate"/>
                        <h1>
                            <field name="license_plate" placeholder="e.g. B 1234 WMS"/>
                        </h1>
                    </div>
                    <group>
                        <group string="Driver Assignment">
                            <field name="driver_id" options="{'no_create_edit': True}"/>
                        </group>
                        <group string="Cargo Capacity">
                            <field name="max_weight"/>
                            <field name="max_volume"/>
                        </group>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <!-- Search View -->
    <record id="view_wms_vehicle_search" model="ir.ui.view">
        <field name="name">wms.vehicle.search</field>
        <field name="model">wms.vehicle</field>
        <field name="arch" type="xml">
            <search string="Search Fleet Vehicles">
                <field name="license_plate"/>
                <field name="driver_id"/>
                <separator/>
                <filter name="filter_available" string="Available / Siap Jalan" domain="[('state', '=', 'available')]"/>
                <filter name="filter_on_delivery" string="On Delivery / Sedang Bertugas" domain="[('state', '=', 'on_delivery')]"/>
                <filter name="filter_maintenance" string="Maintenance / Bengkel" domain="[('state', '=', 'maintenance')]"/>
                <group expand="0" string="Group By">
                    <filter name="group_by_state" string="Status" context="{'group_by': 'state'}"/>
                    <filter name="group_by_driver" string="Driver" context="{'group_by': 'driver_id'}"/>
                </group>
            </search>
        </field>
    </record>

    <!-- Window Action -->
    <record id="action_wms_vehicle" model="ir.actions.act_window">
        <field name="name">Fleet Vehicles</field>
        <field name="res_model">wms.vehicle</field>
        <field name="view_mode">tree,form</field>
        <field name="search_view_id" ref="view_wms_vehicle_search"/>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                Register a new logistics transport vehicle.
            </p>
            <p>
                Manage your fleet, assigned drivers, and weight/volume load capacities for outbound delivery dispatching.
            </p>
        </field>
    </record>

    <!-- Menus -->
    <menuitem id="menu_wms_logistics_root" name="Logistics &amp; Delivery"
              parent="stock.menu_stock_root" sequence="25"/>
    <menuitem id="menu_wms_vehicle" name="Fleet Vehicles"
              parent="menu_wms_logistics_root" action="action_wms_vehicle" sequence="10"/>
</odoo>
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Konflik urutan pemuatan file XML pada manifest. | Low | Mendaftarkan `views/wms_vehicle_views.xml` pada urutan data manifest setelah `stock_picking_views.xml` untuk memastikan dependensi model dan aksi terpenuhi. |
| Pengguna operator tanpa hak modifikasi membuka form. | Low | Telah dijamin oleh aturan ACL di `ir.model.access.csv`: Odoo otomatis merender formulir dalam mode *read-only* bagi pengguna non-manajer/non-dispatcher. |

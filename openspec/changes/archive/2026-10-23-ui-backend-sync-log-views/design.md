# Design Document: Ui Backend Sync Log Views

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | ui-backend-sync-log-views                     |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `sap.sync.log`                                |

## Context
Model ORM `sap.sync.log` beserta method perbaikan `action_retry_sync()` dan pembatasan hak akses berbasis peran (RBAC) pada `security/ir.model.access.csv` telah diimplementasikan dengan sukses pada modul `wms_sap_connector`. Namun, modul belum memiliki subdirektori antarmuka `views/` dan belum mendefinisikan layout XML untuk menampilkan rekaman log transaksi kepada pengguna backend.

Sesuai dengan blueprint arsitektur Two-Tier pada [tsd.md](../../docs/tsd.md) (Bagian 3.2), tim operasional gudang dan administrator sistem membutuhkan antarmuka backend Odoo yang intuitif untuk:
1. Memantau seluruh aliran data masuk (*inbound*) dan keluar (*outbound*) SAP secara visual.
2. Mengidentifikasi transaksi gagal dengan indikasi warna status yang jelas.
3. Memeriksa salinan payload JSON dan pesan galat teknis secara mendalam.
4. Memicu proses pengiriman ulang (*retry*) transaksi gagal langsung dari formulir Odoo tanpa perlu akses terminal database.

## Goals / Non-Goals

### Goals
- Membuat direktori `addons/wms_sap_connector/views` dan file deklarasi antarmuka `sap_sync_log_views.xml`.
- Mengimplementasikan Tree/List view (`view_sap_sync_log_tree`) dengan pewarnaan dekoratif status (`decoration-danger="status == 'failed'"`, `decoration-success="status == 'success'"`, `decoration-warning="status == 'pending'"`).
- Mengimplementasikan Form view (`view_sap_sync_log_form`) dengan statusbar widget, tombol aksi `action_retry_sync` yang dinamis (`invisible="status != 'failed'"`), dan tab notebook untuk payload serta pesan galat.
- Mengimplementasikan Search view (`view_sap_sync_log_search`) dengan filter status, filter arah, dan pengelompokan (*group by*).
- Mendefinisikan Action Window `action_sap_sync_log` dan hierarki menu navigasi di bawah modul Inventory (`stock.menu_stock_root`).
- Mendaftarkan file view XML ke dalam daftar `data` pada `addons/wms_sap_connector/__manifest__.py`.

### Non-Goals
- Tidak mengubah definisi model, tipe field, atau method Python pada `sap.sync.log`.
- Tidak membuat komponen custom JavaScript/OWL frontend khusus (cukup memanfaatkan komponen standar web client Odoo 17).
- Tidak mengubah konfigurasi grup keamanan pengguna atau tabel ACL yang sudah ada.

## Decisions (ADR)

### 1. Penerapan Konvensi Sintaks Deklaratif Odoo 17 Modern
- **Rationale:** Pada Odoo 17, sintaks lama `attrs="{'invisible': ...}"` telah dihapus secara resmi oleh arsitektur web framework Odoo dan digantikan oleh atribut kondisional langsung berbasis ekspresi Python sederhana (contoh: `invisible="status != 'failed'"` dan `readonly="1"`). Mematuhi konvensi modern ini mencegah galat parsing XML saat modul di-upgrade dan menjamin kompatibilitas jangka panjang.
- **Alternatives Considered:** Menggunakan format lama `attrs`: Ditolak karena deprecated dan akan menimbulkan parsing warning/error pada Odoo 17.
- **Consequences:** Seluruh logika keterlihatan tombol aksi dan proteksi edit dideklarasikan secara eksplisit dan ringkas pada atribut tag field/button.

### 2. Desain Form View Berorientasi Audit Forensik (Read-Only Sheet)
- **Rationale:** Rekaman `sap.sync.log` merupakan data audit transaksi pertukaran data dua arah yang harus terjaga integritasnya dari modifikasi langsung oleh manusia. Oleh karena itu, semua kolom informasi pada sheet formulir diset sebagai hanya-baca (`readonly="1"`). Satu-satunya aksi mutasi yang diizinkan bagi pengguna manajerial adalah menekan tombol aksi "Retry Sync" pada header formulir untuk transaksi yang berstatus `failed`.
- **Alternatives Considered:** Mengizinkan pengeditan manual pada field teks payload atau error_message: Ditolak karena berisiko merusak orisinalitas bukti log transaksi integrasi.
- **Consequences:** Log audit bersifat *immutable* terhadap input manual dan hanya berubah status melalui method terkelola `action_retry_sync()`.

### 3. Struktur Hierarki Menu Navigasi Terpadu di Modul Inventory
- **Rationale:** Berdasarkan roadmap, menu log integrasi disematkan di bawah modul utama Inventory. Agar antarmuka rapi dan siap menampung menu integrasi berikutnya (seperti menu pengaturan SAP Host/Token pada Capability 1.3), dibuat struktur menu:
  - Menu Induk: "SAP Integration" (`menu_wms_sap_root`) di bawah `stock.menu_stock_root` dengan sequence 90.
  - Item Menu: "Sync Logs" (`menu_sap_sync_log`) di bawah `menu_wms_sap_root` yang memicu action window `action_sap_sync_log`.
- **Alternatives Considered:** Meletakkan langsung di bawah submenu pelaporan `stock.menu_warehouse_report`: Ditolak karena log integrasi bukan sekadar laporan inventori statis, melainkan pusat kendali eksekusi retry transaksi.
- **Consequences:** Memberikan ruang yang modular dan terisolasi untuk seluruh menu operasional konektor SAP pada modul Inventory Odoo.

## Technical Architecture & Data Schema

### 1. Struktur XML Antarmuka (`addons/wms_sap_connector/views/sap_sync_log_views.xml`)
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Tree / List View -->
    <record id="view_sap_sync_log_tree" model="ir.ui.view">
        <field name="name">sap.sync.log.tree</field>
        <field name="model">sap.sync.log</field>
        <field name="arch" type="xml">
            <tree string="SAP Integration Logs" create="0" edit="0" delete="1"
                  decoration-danger="status == 'failed'"
                  decoration-success="status == 'success'"
                  decoration-warning="status == 'pending'">
                <field name="sync_date"/>
                <field name="name"/>
                <field name="sync_type"/>
                <field name="direction"/>
                <field name="status" widget="badge"
                       decoration-danger="status == 'failed'"
                       decoration-success="status == 'success'"
                       decoration-warning="status == 'pending'"/>
                <field name="error_message"/>
            </tree>
        </field>
    </record>

    <!-- Form View -->
    <record id="view_sap_sync_log_form" model="ir.ui.view">
        <field name="name">sap.sync.log.form</field>
        <field name="model">sap.sync.log</field>
        <field name="arch" type="xml">
            <form string="SAP Integration Log" create="0" edit="0">
                <header>
                    <button name="action_retry_sync" string="Retry Sync" type="object"
                            class="oe_highlight" invisible="status != 'failed'"/>
                    <field name="status" widget="statusbar" statusbar_visible="pending,success,failed"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <label for="name" string="Transaction Reference"/>
                        <h1>
                            <field name="name" readonly="1"/>
                        </h1>
                    </div>
                    <group>
                        <group string="Transaction Metadata">
                            <field name="sync_type" readonly="1"/>
                            <field name="direction" readonly="1"/>
                        </group>
                        <group string="Execution Info">
                            <field name="sync_date" readonly="1"/>
                        </group>
                    </group>
                    <notebook>
                        <page string="Payload (JSON)" name="payload">
                            <field name="payload" readonly="1" placeholder="Payload content..."/>
                        </page>
                        <page string="Error Message" name="error_message" invisible="not error_message">
                            <field name="error_message" readonly="1"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        </field>
    </record>

    <!-- Search View -->
    <record id="view_sap_sync_log_search" model="ir.ui.view">
        <field name="name">sap.sync.log.search</field>
        <field name="model">sap.sync.log</field>
        <field name="arch" type="xml">
            <search string="Search Integration Logs">
                <field name="name" string="Reference"/>
                <field name="error_message" string="Error Details"/>
                <field name="payload" string="Payload Content"/>
                <separator/>
                <filter string="Failed" name="filter_failed" domain="[('status', '=', 'failed')]"/>
                <filter string="Pending" name="filter_pending" domain="[('status', '=', 'pending')]"/>
                <filter string="Success" name="filter_success" domain="[('status', '=', 'success')]"/>
                <separator/>
                <filter string="Inbound" name="filter_inbound" domain="[('direction', '=', 'inbound')]"/>
                <filter string="Outbound" name="filter_outbound" domain="[('direction', '=', 'outbound')]"/>
                <group expand="0" string="Group By">
                    <filter string="Status" name="group_status" context="{'group_by': 'status'}"/>
                    <filter string="Sync Type" name="group_sync_type" context="{'group_by': 'sync_type'}"/>
                    <filter string="Direction" name="group_direction" context="{'group_by': 'direction'}"/>
                    <filter string="Sync Date" name="group_sync_date" context="{'group_by': 'sync_date:day'}"/>
                </group>
            </search>
        </field>
    </record>

    <!-- Window Action -->
    <record id="action_sap_sync_log" model="ir.actions.act_window">
        <field name="name">SAP Integration Logs</field>
        <field name="res_model">sap.sync.log</field>
        <field name="view_mode">tree,form</field>
        <field name="search_view_id" ref="view_sap_sync_log_search"/>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                Belum ada rekaman log integrasi SAP.
            </p>
            <p>
                Log transaksi pertukaran data dua arah antara SAP dan Odoo akan tercatat secara otomatis di sini.
            </p>
        </field>
    </record>

    <!-- Menus -->
    <menuitem id="menu_wms_sap_root" name="SAP Integration"
              parent="stock.menu_stock_root" sequence="90"/>
    <menuitem id="menu_sap_sync_log" name="Sync Logs"
              parent="menu_wms_sap_root" action="action_sap_sync_log" sequence="10"/>
</odoo>
```

### 2. Registrasi Manifest (`addons/wms_sap_connector/__manifest__.py`)
```python
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/sap_sync_log_views.xml",
    ],
```

## Risks & Trade-offs

| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Kesalahan parsing XML akibat sintaks usang (`attrs`) pada Odoo 17 | High | Menggunakan atribut kondisional modern Odoo 17 seperti `invisible="status != 'failed'"`. |
| Duplikasi menu ID atau salah referensi parent menu | Medium | Merujuk secara presisi ke menu root modul stock Odoo (`stock.menu_stock_root`). |
| Tombol aksi Retry Sync memicu eksekusi pada record non-gagal | Low | Divalidasi ganda: di level view tombol disembunyikan (`invisible="status != 'failed'"`), dan di level model divalidasi dengan `UserError`. |

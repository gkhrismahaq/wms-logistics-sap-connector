# Design Document: Setup Sap Connector Settings

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | setup-sap-connector-settings                  |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `res.config.settings`                         |

## Context
Modul `wms_sap_connector` telah menyelesaikan infrastruktur dasar model audit log `sap.sync.log`, kontrol akses berbasis peran (RBAC), serta antarmuka visual backend. Pada arsitektur Two-Tier ERP yang dijelaskan pada [tsd.md](../../docs/tsd.md) (Bagian 3.2), Odoo perlu mengirimkan konfirmasi transaksi dan webhook Goods Issue (GI) ke host SAP / simulator FastAPI.

Agar komunikasi ini tidak bergantung pada nilai yang di-hardcode (*hardcoded values*), diperlukan mekanisme konfigurasi terpusat yang memungkinkan administrator mengatur URL dasar host SAP (`sap_base_url`) dan token otorisasi API (`sap_api_token`). Pada Odoo 17, pola baku untuk parameter sistem ini adalah memperluas model transient `res.config.settings` dengan atribut `config_parameter` yang otomatis tersimpan pada tabel `ir.config_parameter`.

## Goals / Non-Goals

### Goals
- Mengimplementasikan model `ResConfigSettings` yang mewarisi `res.config.settings` pada `addons/wms_sap_connector/models/res_config_settings.py`.
- Mendefinisikan field `sap_base_url` (`config_parameter='wms_sap_connector.sap_base_url'`) dan `sap_api_token` (`config_parameter='wms_sap_connector.sap_api_token'`).
- Mengimplementasikan view XML `addons/wms_sap_connector/views/res_config_settings_views.xml` yang mewarisi `stock.res_config_settings_view_form` untuk menambahkan blok pengaturan "SAP Integration Connector" pada panel Settings Inventory.
- Menerapkan perlindungan masking password pada input field `sap_api_token`.
- Mendaftarkan model dan view baru pada package `models/__init__.py` dan manifest `__manifest__.py`.

### Non-Goals
- Tidak mengimplementasikan pemanggilan webhook HTTP atau endpoint API pada change ini (logika panggilan jaringan dialokasikan pada fase integrasi endpoint).
- Tidak memodifikasi tabel model transaksi `sap.sync.log`.
- Tidak membuat aplikasi settings mandiri di luar menu pengaturan Inventory Odoo bawaan.

## Decisions (ADR)

### 1. Penyimpanan Parameter Konfigurasi Menggunakan config_parameter Odoo 17
- **Rationale:** Odoo 17 menyediakan fitur bawaan `config_parameter` pada field deklaratif `res.config.settings`. Dengan menentukan parameter ini, Odoo secara otomatis mengurus persistensi data ke tabel `ir.config_parameter` (System Parameters) saat tombol "Save" ditekan, serta mengambil kembali nilainya saat formulir Settings dibuka tanpa perlu menulis method override `get_values()` dan `set_values()`. Di level service backend, nilai ini dapat diambil dengan aman via `env['ir.config_parameter'].sudo().get_param('wms_sap_connector.sap_base_url')`.
- **Alternatives Considered:** Membuat tabel basis data mandiri (`sap.connector.settings`): Ditolak karena menciptakan kompleksitas yang tidak perlu (*over-engineering*) untuk sekadar menyimpan parameter koneksi global tunggal.
- **Consequences:** Kredensial dan endpoint host tersimpan secara persisten dan dapat diubah secara dinamis tanpa restart server.

### 2. Integrasi Panel Pengaturan ke Menu Settings Inventory (stock.res_config_settings_view_form)
- **Rationale:** Sesuai panduan roadmap, konfigurasi konektor SAP ditempatkan pada panel pengaturan Inventory. Menggunakan inheritance XPath pada view `stock.res_config_settings_view_form` di dalam container `<app name="stock">` memastikan bagian konfigurasi SAP menyatu rapi dengan pengaturan inventori lainnya (*Operations*, *Barcode*, dll.) yang diakses melalui menu *Inventory > Configuration > Settings*.
- **Alternatives Considered:** Menambahkan tab aplikasi baru di menu Settings umum Odoo: Ditolak karena parameter ini berkaitan langsung dengan alur logistik & inventori WMS, sehingga lebih koheren bila digabungkan pada panel Inventory.
- **Consequences:** Administrator gudang dapat mengelola koneksi SAP dari antarmuka pengaturan inventori yang sudah mereka kenal.

### 3. Masking Kredensial Token API
- **Rationale:** `sap_api_token` berfungsi sebagai kunci otentikasi Bearer rahasia antara Odoo dan SAP. Menampilkan token ini dalam bentuk teks terbuka di antarmuka berpotensi menimbulkan celah kebocoran (*credential exposure*). Atribut `password="True"` diterapkan pada view XML agar input token disamarkan dengan karakter titik (*bullet dots*).
- **Alternatives Considered:** Menampilkan token dalam field teks biasa (*plain text*): Ditolak demi mematuhi standar *security hygiene* enterprise.
- **Consequences:** Token tidak dapat dibaca langsung dari layar oleh pihak yang melintas di sekitar layar monitor administrator.

## Technical Architecture & Data Schema

### 1. Kelas Model Konfigurasi (`addons/wms_sap_connector/models/res_config_settings.py`)
```python
# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sap_base_url = fields.Char(
        string="SAP Base URL",
        config_parameter="wms_sap_connector.sap_base_url",
        help="URL host server SAP / FastAPI simulator (misal: http://localhost:8000).",
    )
    sap_api_token = fields.Char(
        string="SAP API Token",
        config_parameter="wms_sap_connector.sap_api_token",
        help="Token rahasia otentikasi untuk otorisasi webhook dari Odoo ke SAP.",
    )
```

### 2. Tampilan Pengaturan XML (`addons/wms_sap_connector/views/res_config_settings_views.xml`)
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="res_config_settings_view_form" model="ir.ui.view">
        <field name="name">res.config.settings.view.form.inherit.wms.sap</field>
        <field name="model">res.config.settings</field>
        <field name="priority" eval="90"/>
        <field name="inherit_id" ref="stock.res_config_settings_view_form"/>
        <field name="arch" type="xml">
            <xpath expr="//app[@name='stock']" position="inside">
                <block title="SAP Integration Connector" name="sap_connector_settings_block">
                    <setting id="sap_base_url_setting" help="URL host server SAP / FastAPI simulator (misal: http://localhost:8000)">
                        <field name="sap_base_url" placeholder="http://localhost:8000"/>
                    </setting>
                    <setting id="sap_api_token_setting" help="Token rahasia otentikasi untuk otorisasi webhook dari Odoo ke SAP">
                        <field name="sap_api_token" password="True" placeholder="Masukkan token rahasia"/>
                    </setting>
                </block>
            </xpath>
        </field>
    </record>
</odoo>
```

### 3. Pendaftaran Manifest (`addons/wms_sap_connector/__manifest__.py`)
```python
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/sap_sync_log_views.xml",
        "views/res_config_settings_views.xml",
    ],
```

## Risks & Trade-offs

| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Kesalahan target XPath pada Odoo 17 settings view | Medium | Menggunakan target ekspresi XPath `//app[@name='stock']` yang valid pada Odoo 17 view form stock. |
| Nilai URL tidak valid (tanpa skema http/https) | Low | Menyediakan placeholder eksplisit (`http://localhost:8000`) dan dokumentasi help text yang jelas. |
| Parameter hilang saat upgrade modul | Low | Menggunakan mekanisme standar `ir.config_parameter` yang menyimpan nilai di basis data dan tidak terhapus saat pembaruan modul. |

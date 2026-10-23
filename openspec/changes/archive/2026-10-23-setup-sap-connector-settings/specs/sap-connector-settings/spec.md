# Specification: Sap Connector Settings

## Purpose
Menyediakan antarmuka konfigurasi terpusat pada menu Settings Odoo dan penyimpanan parameter sistem yang persisten untuk mengelola URL endpoint host server SAP serta token otentikasi API secara aman.

## ADDED Requirements

### Requirement: [REQ-SETTING-01] Konfigurasi Parameter Terpusat Endpoint dan Kredensial SAP
The system MUST memperluas model `res.config.settings` dengan menambahkan bidang data `sap_base_url` dan `sap_api_token` yang terikat secara persisten pada tabel parameter sistem `ir.config_parameter`, serta menyajikannya pada antarmuka pengaturan Inventory.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Spesifikasi teknis atribut konfigurasi:
- `sap_base_url` (Char, `config_parameter='wms_sap_connector.sap_base_url'`): Menyimpan URL dasar server SAP atau simulator FastAPI (contoh: `http://localhost:8000`).
- `sap_api_token` (Char, `config_parameter='wms_sap_connector.sap_api_token'`): Menyimpan token rahasia otentikasi untuk otorisasi webhook dari Odoo ke SAP.
- Antarmuka formulir MUST menerapkan masking password pada bidang `sap_api_token` untuk menjaga kerahasiaan kredensial.
- Akses pengubahan parameter dibatasi hanya untuk pengguna dengan wewenang manajerial atau administratif (`stock.group_stock_manager` atau `base.group_system`).

#### Scenario: Penyimpanan dan Pembaruan Konfigurasi Konektor SAP
- **GIVEN** pengguna dengan hak administratif membuka menu Settings Inventory Odoo
- **WHEN** pengguna mengisikan nilai endpoint host pada `sap_base_url` dan token otorisasi pada `sap_api_token` lalu menekan tombol "Save"
- **THEN** sistem menyimpan nilai tersebut secara persisten ke dalam `ir.config_parameter` dengan kunci `wms_sap_connector.sap_base_url` dan `wms_sap_connector.sap_api_token`

#### Scenario: Pembacaan Konfigurasi SAP yang Tersimpan
- **GIVEN** parameter koneksi SAP telah tersimpan sebelumnya pada basis data
- **WHEN** administrator membuka kembali halaman Settings Inventory
- **THEN** sistem memuat dan menampilkan nilai `sap_base_url` yang tersimpan serta menampilkan field `sap_api_token` dengan tampilan tersembunyi (*password masked*)

#### Scenario: Pembatasan Akses Modifikasi Konfigurasi
- **GIVEN** pengguna sistem tanpa wewenang administratif manajer gudang
- **WHEN** pengguna mencoba mengakses atau memperbarui parameter koneksi SAP
- **THEN** sistem Odoo menolak akses pengubahan formulir Settings sesuai batasan hak akses keamanan

## MODIFIED Requirements
None

## REMOVED Requirements
None

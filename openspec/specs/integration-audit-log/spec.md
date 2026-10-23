# Specification: Integration Audit Log

## Purpose
Menyediakan infrastruktur pencatatan rekaman audit transaksi pertukaran data dua arah antara SAP dan Odoo beserta mekanisme pengiriman ulang transaksi galat untuk menjamin transparansi, integritas, dan kemampuan rekonsiliasi data.

## Requirements

### Requirement: [REQ-AUDIT-01] Model Entitas Audit Log Sinkronisasi SAP
The system MUST mendefinisikan model ORM Odoo `sap.sync.log` untuk mencatat seluruh riwayat pertukaran data dua arah antara SAP dan Odoo dengan bidang data `name`, `sync_type`, `direction`, `payload`, `status`, `error_message`, dan `sync_date`.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Atribut model `sap.sync.log` meliputi:
- `name` (Char, Required): Nomor referensi unik transaksi atau nama log.
- `sync_type` (Selection, Required): Jenis integrasi (`master_product`, `master_partner`, `inbound_po`, `outbound_so`).
- `direction` (Selection, Required): Arah pertukaran data (`inbound` untuk SAP ke Odoo, `outbound` untuk Odoo ke SAP).
- `payload` (Text): Salinan lengkap struktur payload JSON data yang dipertukarkan.
- `status` (Selection, Required, Default: `pending`): Status transaksi (`pending`, `success`, `failed`).
- `error_message` (Text): Rekaman pesan kegagalan teknis jika transaksi mengalami galat.
- `sync_date` (Datetime, Default: waktu saat record dibuat): Waktu pencatatan log integrasi.

#### Scenario: Pencatatan Audit Log Sukses
- **GIVEN** sebuah transaksi data integrasi masuk (*inbound*) atau keluar (*outbound*) diproses oleh sistem
- **WHEN** data transaksi disimpan ke dalam model `sap.sync.log` dengan status `success`
- **THEN** sistem berhasil menyimpan rekaman lengkap beserta waktu `sync_date`, arah transaksi, tipe sinkronisasi, dan payload JSON tanpa galat

#### Scenario: Pencatatan Transaksi Integrasi Gagal
- **GIVEN** sebuah transaksi integrasi mengalami kegagalan akibat galat jaringan, validasi data, atau penolakan API
- **WHEN** sistem mencatat kegagalan tersebut ke model `sap.sync.log`
- **THEN** sistem menyimpan status sebagai `failed`, merekam rincian galat pada field `error_message`, dan menyimpan snapshot `payload` JSON yang dipertukarkan

### Requirement: [REQ-AUDIT-02] Mekanisme Retry Transaksi Sinkronisasi Gagal
The system MUST menyediakan method `action_retry_sync()` pada model `sap.sync.log` yang dapat dieksekusi pada record transaksi dengan status `failed` untuk memicu pemrosesan atau pengiriman ulang data ke sistem target.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

#### Scenario: Pemicuan Retry pada Log Berstatus Gagal
- **GIVEN** sebuah record `sap.sync.log` memiliki status `failed`
- **WHEN** method `action_retry_sync()` dieksekusi pada record tersebut
- **THEN** sistem menerima permintaan eksekusi ulang, memperbarui status menjadi `pending`, dan menyiapkan pemrosesan ulang data

#### Scenario: Penolakan Retry pada Transaksi Bukan Berstatus Gagal
- **GIVEN** sebuah record `sap.sync.log` memiliki status `success`
- **WHEN** pengguna atau sistem memanggil method `action_retry_sync()` pada record tersebut
- **THEN** sistem menolak tindakan dengan melempar pengecualian peringatan (UserError) dan mempertahankan integritas data log tanpa perubahan status

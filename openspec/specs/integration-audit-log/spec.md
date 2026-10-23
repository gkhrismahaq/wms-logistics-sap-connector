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

### Requirement: [REQ-AUDIT-03] Konfigurasi Grup Keamanan Pengguna dan Hak Akses Model Log
The system MUST mendefinisikan kategori modul keamanan `module_category_wms_logistics` dan grup otorisasi pengguna untuk peran Warehouse Operator (`group_wms_operator`), Logistics Dispatcher (`group_wms_dispatcher`), dan Warehouse Manager (`group_wms_manager`), serta mengonfigurasi Access Control List (ACL) pada `security/ir.model.access.csv` guna mengatur izin akses model `sap.sync.log`.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.6

Ketentuan matriks hak akses model `sap.sync.log`:
- Warehouse Manager (`group_wms_manager`): Hak akses penuh CRUD (`perm_read=1`, `perm_write=1`, `perm_create=1`, `perm_unlink=1`).
- Administrator Sistem (`base.group_system`): Hak akses penuh CRUD (`perm_read=1`, `perm_write=1`, `perm_create=1`, `perm_unlink=1`).
- Warehouse Operator (`group_wms_operator`): Hak akses baca saja (`perm_read=1`, `perm_write=0`, `perm_create=0`, `perm_unlink=0`) untuk visibilitas status operasional.
- Logistics Dispatcher (`group_wms_dispatcher`): Hak akses baca saja (`perm_read=1`, `perm_write=0`, `perm_create=0`, `perm_unlink=0`) untuk pemantauan dokumen pengiriman.
- Pengguna umum tanpa grup terkait MUST NOT memiliki izin akses baca maupun tulis terhadap model `sap.sync.log`.

Hierarki grup:
- `group_wms_manager` mewarisi kewenangan dari `group_wms_operator` dan `group_wms_dispatcher` melalui relasi `implied_ids`.

#### Scenario: Akses Penuh CRUD Log Audit oleh Warehouse Manager
- **GIVEN** pengguna terotentikasi dan memiliki keanggotaan dalam grup `group_wms_manager`
- **WHEN** pengguna melakukan operasi baca (*read*), penambahan (*create*), pengubahan (*write*), atau penghapusan (*unlink*) pada record `sap.sync.log`
- **THEN** sistem Odoo mengizinkan seluruh operasi tersebut berjalan sukses sesuai hak akses administratif penuh

#### Scenario: Akses Terbatas Baca Saja oleh Warehouse Operator dan Logistics Dispatcher
- **GIVEN** pengguna terotentikasi dan memiliki keanggotaan dalam grup `group_wms_operator` atau `group_wms_dispatcher`
- **WHEN** pengguna mencoba membaca record pada model `sap.sync.log`
- **THEN** sistem Odoo mengizinkan pembacaan record, namun jika pengguna mencoba menambah, mengubah, atau menghapus record, sistem secara otomatis menolak dengan melempar pengecualian `AccessError`

#### Scenario: Penolakan Akses oleh Pengguna Tanpa Otorisasi Grup WMS
- **GIVEN** pengguna sistem internal Odoo yang tidak tergabung dalam grup `group_wms_manager`, `group_wms_operator`, maupun `group_wms_dispatcher`
- **WHEN** pengguna mencoba melakukan operasi query atau manipulasi data pada model `sap.sync.log`
- **THEN** sistem Odoo menolak akses secara mutlak dengan melempar pengecualian `AccessError`

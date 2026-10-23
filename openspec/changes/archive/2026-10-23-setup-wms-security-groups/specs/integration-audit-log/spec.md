# Specification: Integration Audit Log

## Purpose
Menyediakan tata kelola keamanan dan pembatasan hak akses berbasis peran (*Role-Based Access Control*) untuk mengamankan model data log integrasi SAP, serta mendefinisikan hierarki grup pengguna operasional gudang dan logistik.

## ADDED Requirements

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

## MODIFIED Requirements
None

## REMOVED Requirements
None

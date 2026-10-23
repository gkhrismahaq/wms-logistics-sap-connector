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

### Requirement: [REQ-AUDIT-04] Antarmuka Tampilan Backend dan Menu Navigasi Audit Log Sinkronisasi SAP
The system MUST menyediakan antarmuka pengguna backend Odoo yang mencakup Tree/List view, Form view interaktif dengan tombol "Retry Sync", Search view dengan filter dan pengelompokan lengkap, serta penyematan menu navigasi "SAP Integration Logs" di bawah modul Inventory (`stock.menu_stock_root`).
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Spesifikasi antarmuka visual:
1. **Tree/List View (`view_sap_sync_log_tree`)**:
   - Menampilkan kolom data: `sync_date`, `name`, `sync_type`, `direction`, `status`, dan `error_message`.
   - Menerapkan dekorasi warna visual berbasis status: `decoration-danger="status == 'failed'"`, `decoration-success="status == 'success'"`, dan `decoration-warning="status == 'pending'"`.
2. **Form View (`view_sap_sync_log_form`)**:
   - Header form memuat statusbar widget untuk bidang `status` (`statusbar_visible="pending,success,failed"`).
   - Memuat tombol aksi "Retry Sync" (`action_retry_sync`) bertipe `object` dengan styling `oe_highlight`, yang secara dinamis hanya ditampilkan saat record berstatus gagal (`invisible="status != 'failed'"`).
   - Menampilkan bidang informasi transaksi (`name`, `sync_type`, `direction`, `sync_date`) dalam format terstruktur.
   - Menyediakan notebook dengan tab terpisah untuk peninjauan `payload` (JSON) dan rekaman `error_message`.
3. **Search View (`view_sap_sync_log_search`)**:
   - Fitur pencarian teks berdasarkan referensi transaksi (`name`), `error_message`, dan `payload`.
   - Filter cepat untuk status transaksi (`Failed`, `Pending`, `Success`) dan arah aliran data (`Inbound`, `Outbound`).
   - Fitur pengelompokan (*Group By*) berdasarkan Status, Tipe Sinkronisasi (*Sync Type*), Arah (*Direction*), dan Tanggal (*Sync Date*).
4. **Action Window & Navigasi Menu**:
   - Action window `action_sap_sync_log` mengarahkan pengguna ke model `sap.sync.log` dengan urutan tampilan `tree,form`.
   - Menu navigasi "SAP Integration Logs" disematkan di bawah modul Inventory (`stock.menu_stock_root`) agar mudah diakses oleh operator dan manajer gudang.

#### Scenario: Visualisasi dan Penelusuran Log Transaksi pada Tree View
- **GIVEN** sejumlah rekaman transaksi integrasi telah tersimpan di dalam model `sap.sync.log`
- **WHEN** pengguna berwenang mengakses menu navigasi "SAP Integration Logs"
- **THEN** sistem menampilkan daftar catatan transaksi dalam format Tree View lengkap dengan indikator warna status, tanggal transaksi, arah data, dan ringkasan pesan galat

#### Scenario: Penanganan Transaksi Gagal Melalui Form View
- **GIVEN** sebuah rekaman transaksi integrasi memiliki status `failed`
- **WHEN** pengguna membuka detail rekaman tersebut pada Form View
- **THEN** sistem menyajikan tombol aksi "Retry Sync" pada bagian header form serta menampilkan rincian pesan kesalahan dan payload JSON pada tab notebook

#### Scenario: Sembunyikan Tombol Retry pada Transaksi Sukses atau Menunggu
- **GIVEN** sebuah rekaman transaksi integrasi memiliki status `success` atau `pending`
- **WHEN** pengguna membuka tampilan Form View rekaman tersebut
- **THEN** sistem secara otomatis menyembunyikan tombol aksi "Retry Sync" guna mencegah pengiriman ulang transaksi yang tidak semestinya

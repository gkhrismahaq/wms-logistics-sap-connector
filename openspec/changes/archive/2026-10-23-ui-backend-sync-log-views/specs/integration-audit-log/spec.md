# Specification: Integration Audit Log

## Purpose
Menyediakan antarmuka visual backend grafis (Tree, Form, Search View) dan menu navigasi terintegrasi pada modul Inventory Odoo untuk memfasilitasi pemantauan, penyaringan, dan penanganan ulang galat (*retry*) log transaksi integrasi SAP.

## ADDED Requirements

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

## MODIFIED Requirements
None

## REMOVED Requirements
None

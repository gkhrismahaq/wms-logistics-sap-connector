# Specification: Inbound Goods Receipt

## ADDED Requirements

### Requirement: [REQ-INB-06] Alokasi Rak Simpan Otomatis Berbasis Putaway Rule pada Dokumen Penerimaan
The system MUST mengeksekusi resolusi aturan penempatan rak (*Putaway Rule*) saat dokumen penerimaan barang masuk (*Stock Receipt*) diterbitkan atau dikonfirmasi, serta mengarahkan lokasi tujuan fisik pada baris perpindahan (`stock.move.line.location_dest_id`) ke rak atau bin spesifik yang telah dipetakan.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.2

Spesifikasi teknis resolusi rak penempatan:
- Saat pembuatan dokumen picking masuk via API (`create_inbound_from_sap`) atau konfirmasi dokumen (`action_confirm()`), sistem mengevaluasi model `stock.putaway.rule` berdasarkan produk (`product_id`) atau kategori produk (`category_id`) yang masuk ke lokasi gudang penerimaan (`location_in_id`).
- Jika aturan penempatan cocok ditemukan, sistem MUST menetapkan lokasi tujuan baris detail operasi fisik (`stock.move.line.location_dest_id`) ke lokasi rak tujuan (`location_out_id`).
- Jika tidak ada aturan putaway yang cocok, sistem MUST mengarahkan lokasi tujuan secara aman (*fallback*) ke lokasi stok internal induk gudang (`stock.warehouse.lot_stock_id`).

#### Scenario: Penempatan Otomatis Produk ke Rak Spesifik Saat Dokumen Receipt Dikonfirmasi
- **GIVEN** produk dengan kode SAP `MAT-KOPI-01` memiliki aturan putaway aktif yang memetakan kedatangan di gudang `DCLOW/Stock` ke rak tujuan `DCLOW/Stock/Shelf 1`
- **WHEN** dokumen penerimaan inbound dibuat dan dikonfirmasi (`action_confirm()`)
- **THEN** sistem secara otomatis menetapkan lokasi tujuan pada baris detail operasi (`stock.move.line.location_dest_id`) ke rak `DCLOW/Stock/Shelf 1`

#### Scenario: Fallback ke Lokasi Stok Induk Saat Aturan Putaway Belum Didefinisikan
- **GIVEN** sebuah produk dari SAP belum memiliki aturan penempatan rak spesifik yang terdaftar di database
- **WHEN** dokumen penerimaan inbound untuk produk tersebut dibuat dan dikonfirmasi
- **THEN** sistem secara otomatis menetapkan lokasi tujuan baris operasi ke lokasi stok induk gudang (`DCLOW/Stock`) sehingga alur transaksi tetap berhasil tanpa galat

### Requirement: [REQ-INB-07] Konfigurasi Data Aturan Putaway dan Visibilitas Alokasi Rak pada Dokumen Operasi Gudang
The system MUST menyediakan data konfigurasi awal (*data seed*) aturan putaway untuk material standar SAP dan memastikan lokasi rak tujuan (*Destination Location*) ditampilkan secara transparan pada formulir operasi transfer dokumen penerimaan guna memandu staf pemindai barcode / penata rak fisik di lantai gudang.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.2, 3.2, 3.6

Spesifikasi teknis konfigurasi dan antarmuka:
- Data Seed Aturan Putaway (`stock.putaway.rule`): Modul menyediakan file data XML yang memetakan material cepat saji / makanan kering ke `Shelf 1` dan material lainnya ke `Shelf 2`.
- Visibilitas Antarmuka: Kolom lokasi tujuan rak fisik ditampilkan secara jelas pada tab *Operations* dan *Detailed Operations* formulir transfer dokumen penerimaan (`stock.view_picking_form`).
- Kontrol Hak Akses: Hak akses model `stock.putaway.rule` dikonfigurasikan pada `security/ir.model.access.csv` di mana `Warehouse Manager` (`group_wms_manager`) memiliki hak kelola penuh (CRUD), sedangkan `Warehouse Operator` (`group_wms_operator`) memiliki hak baca (Read-only).

#### Scenario: Operator Memeriksa Alokasi Rak Tujuan pada Antarmuka Dokumen Penerimaan
- **GIVEN** dokumen penerimaan barang berstatus `assigned` (Ready) telah selesai diproses oleh sistem
- **WHEN** operator gudang membuka detail dokumen penerimaan pada antarmuka *Transfers / Receipts*
- **THEN** operator melihat lokasi rak simpan spesifik (contoh: `DCLOW/Stock/Shelf 1`) pada baris operasi transfer untuk memandu proses peletakan fisik barang

#### Scenario: Pembatasan Hak Akses Modifikasi Aturan Putaway
- **GIVEN** pengguna dengan peran `Warehouse Operator` (`group_wms_operator`) mengakses sistem
- **WHEN** pengguna mencoba menambah atau mengubah konfigurasi aturan penempatan rak (*Putaway Rule*)
- **THEN** sistem membatasi akses hanya untuk melihat (read-only) dan menolak operasi modifikasi atau penghapusan aturan

## MODIFIED Requirements
None

## REMOVED Requirements
None

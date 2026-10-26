# Specification: Outbound Dispatch Surat Jalan

## Purpose
Menyediakan kemampuan penerimaan instruksi pengiriman pesanan penjualan (*Sales Delivery Request*) dari SAP Upper Line melalui antarmuka REST API, konversi otomatis menjadi dokumen pengeluaran barang (*Delivery Order*) di Odoo 17, serta pencatatan jejak audit transaksi secara komprehensif.

## Requirements

### Requirement: [REQ-OUT-01] Penerimaan Instruksi Pengiriman Pesanan Penjualan dari SAP via Endpoint REST API
The system MUST menyediakan endpoint REST API publik `POST /api/sap/outbound/delivery` yang aman dan terautentikasi untuk menerima payload JSON instruksi pengiriman kargo dari SAP Upper Line.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.5.3

Spesifikasi protokol dan muatan request:
- Header HTTP:
  - `Content-Type: application/json`
  - `X-Odoo-API-Key: <token>` atau `Authorization: Bearer <token>` (harus cocok dengan parameter sistem `wms_sap_connector.sap_api_token`).
- Format Payload JSON:
  - `sap_doc_number` (String, Wajib): Nomor referensi pesanan pengiriman penjualan SAP (contoh: `"SO-DELIV-2026-901"`).
  - `customer_code` (String, Wajib): Nomor identitas unik pelanggan pada SAP (contoh: `"CUST-ALFAMART-01"`).
  - `destination_city` (String, Opsional): Nama kota tujuan pengantaran (contoh: `"Jakarta Barat"`).
  - `items` (List of Objects, Wajib): Daftar rincian barang pesanan:
    - `sap_material_code` (String, Wajib): Kode unik material produk SAP (contoh: `"MAT-KOPI-01"`).
    - `qty` (Float, Wajib, > 0): Jumlah kuantitas kargo yang harus dikirim.
    - `uom` (String, Opsional): Satuan unit pengukuran.

Spesifikasi format respon JSON:
- HTTP 200 (Sukses Baru / Idempoten):
  - `status`: `"SUCCESS"`
  - `code`: `200`
  - `message`: `"Delivery Order created successfully"` atau `"Delivery Order already exists (idempotent)"`
  - `picking_id`: Integer ID dokumen `stock.picking`
  - `picking_name`: Nama referensi dokumen (contoh: `"DCLOW/OUT/0001"`)
  - `sap_doc_number`: Nomor dokumen SAP terkait
  - `sync_ref`: Nomor referensi sinkronisasi audit log
- HTTP 400 (Bad Request):
  - `status`: `"ERROR"`
  - `code`: `400`
  - `message`: Pesan deskriptif kegagalan validasi (misal field wajib hilang atau pelanggan/material tidak terdaftar).
- HTTP 401 (Unauthorized):
  - `status`: `"ERROR"`
  - `code`: `401`
  - `message`: `"Unauthorized: Invalid or missing API token"`

#### Scenario: Penerimaan Instruksi Delivery Order Baru yang Valid (Happy Path)
- **GIVEN** sistem telah mengonfigurasi token API SAP yang valid dan master data Customer serta Material telah terdaftar
- **WHEN** client SAP mengirimkan permintaan HTTP POST ke `/api/sap/outbound/delivery` dengan payload lengkap dan header token yang sah
- **THEN** sistem mengembalikan respon HTTP 200 berisi ID picking dan referensi log sinkronisasi

#### Scenario: Permintaan Ditolak Akibat Kredensial Tidak Sah (Unauthorized)
- **GIVEN** panggilan API ke endpoint `/api/sap/outbound/delivery` tanpa menyertakan header token atau dengan token yang salah
- **WHEN** request dieksekusi ke server
- **THEN** sistem menolak permintaan dengan respon HTTP 401 Unauthorized dan mencatat percobaan gagal ke audit log

#### Scenario: Penolakan Payload Akibat Data Pelanggan atau Material Tidak Ditemukan (Edge Case)
- **GIVEN** payload JSON memuat `customer_code` atau `sap_material_code` yang tidak ada di master data Odoo
- **WHEN** server memproses request tersebut
- **THEN** sistem membatalkan pembuatan dokumen, mengembalikan respon HTTP 400 Bad Request berisi rincian kode yang hilang, dan mencatat galat ke audit log

### Requirement: [REQ-OUT-02] Konversi Otomatis dan Idempotensi Dokumen Delivery Order (stock.picking)
The system MUST mengonversi data instruksi pengiriman SAP menjadi dokumen pengeluaran barang (`stock.picking` dengan tipe operasi `outgoing`), memetakan partner pelanggan serta pergerakan stok (`stock.move`), dan menerapkan mekanisme idempoten berdasarkan nomor dokumen SAP (`sap_doc_number`).
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.3, 3.2

Spesifikasi logika pembuatan dokumen:
- Dokumen Picking (`stock.picking`):
  - `picking_type_id`: Tipe operasi `outgoing` pada gudang `DCLOW` (Delivery Orders).
  - `partner_id`: Mitra pelanggan `res.partner` yang memiliki `sap_partner_code == customer_code`.
  - `origin`: Nilai `sap_doc_number`.
  - `sap_doc_number`: Nilai `sap_doc_number`.
  - `sap_sync_status`: Nilai `'draft'`.
  - `location_id`: Lokasi sumber stok gudang (`stock_location`).
  - `location_dest_id`: Lokasi tujuan pelanggan (`stock.stock_location_customers`).
- Baris Pergerakan Stok (`stock.move`):
  - Diterbitkan untuk setiap baris pada daftar `items`.
  - `product_id`: Produk yang cocok dengan `sap_material_code`.
  - `product_uom_qty`: Nilai `qty` dari payload.
  - `product_uom`: Satuan UoM bawaan produk (`product_id.uom_id`).
- Idempotensi:
  - Sebelum membuat record baru, sistem memeriksa keberadaan dokumen `stock.picking` dengan `sap_doc_number` dan tipe `outgoing`.
  - Jika dokumen sudah ada, sistem tidak membuat duplikat, melainkan mengembalikan record yang sudah ada dengan penanda idempoten.
- Lifecycle Dokumen:
  - Setelah pembuatan moves, sistem memicu `action_confirm()` dan `action_assign()` untuk melakukan reservasi stok.

#### Scenario: Pembuatan Dokumen Delivery Order Baru Beserta Stock Moves (Happy Path)
- **GIVEN** instruksi pengiriman dari SAP dengan nomor `SO-DELIV-2026-901` dan 2 item material
- **WHEN** method pembuatan dokumen dieksekusi
- **THEN** sistem menerbitkan dokumen `stock.picking` bertipe `outgoing` dengan 2 baris `stock.move`, status dokumen menjadi `assigned` atau `confirmed`, dan `sap_doc_number` tersimpan

#### Scenario: Pencegahan Duplikasi Dokumen Melalui Idempotensi (Idempotent Path)
- **GIVEN** dokumen pengiriman dengan `sap_doc_number = 'SO-DELIV-2026-901'` telah tercatat di sistem
- **WHEN** client SAP mengirimkan kembali payload dengan nomor dokumen yang sama persis
- **THEN** sistem mendeteksi keberadaan record eksisting, tidak membuat dokumen baru, dan mengembalikan data dokumen yang sudah ada dengan respon HTTP 200

### Requirement: [REQ-OUT-03] Pencatatan Jejak Audit Sinkronisasi Transaksi Outbound ke sap.sync.log
The system MUST mendokumentasikan seluruh riwayat pertukaran data instruksi pengiriman keluar ke dalam model audit `sap.sync.log` dengan jenis sinkronisasi `outbound_so` dan arah aliran `inbound`.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Spesifikasi audit log:
- `name`: Nomor referensi sinkronisasi berformat unik `SYNC-SO-{YYYYMMDD}-{UUID}`.
- `sync_type`: Nilai konstan `outbound_so`.
- `direction`: Nilai konstan `inbound`.
- `payload`: Salinan teks JSON request asli yang diterima dari SAP.
- `status`: `success` jika transaksi berhasil dibuat/idempoten, atau `failed` jika terjadi galat autentikasi atau validasi.
- `error_message`: Pesan deskriptif kegagalan jika status bernilai `failed`.
- `sync_date`: Timestamp waktu eksekusi transaksi.

#### Scenario: Pencatatan Log Sukses Transaksi Delivery Order
- **GIVEN** panggilan API instruksi pengiriman berhasil diproses
- **WHEN** respon sukses dikembalikan ke client
- **THEN** terdapat record baru di `sap.sync.log` dengan status `success` dan referensi sinkronisasi `SYNC-SO-...`

#### Scenario: Pencatatan Log Galat Transaksi yang Gagal Diproses
- **GIVEN** panggilan API gagal akibat material tidak ditemukan
- **WHEN** eksepsi validasi tertangkap oleh controller
- **THEN** sistem mencatat payload dan pesan error ke record `sap.sync.log` berstatus `failed` sebelum merespon HTTP 400

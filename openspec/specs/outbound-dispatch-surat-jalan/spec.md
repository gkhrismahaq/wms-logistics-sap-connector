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

### Requirement: [REQ-OUT-04] Penugasan Armada Kendaraan dan Supir Pengantar pada Dokumen Delivery Order (stock.picking)
The system MUST menyediakan atribut relasional penugasan armada kendaraan kargo (`vehicle_id`) dan supir pengantar (`driver_id`) pada dokumen transfer `stock.picking` beserta otomatisasi penetapan supir default.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Spesifikasi atribut dan relasi:
- `vehicle_id` (Many2one -> `wms.vehicle`):
  - Label: `"Vehicle / Fleet"`
  - Domain penyaringan: hanya menampilkan armada yang tidak sedang dalam perawatan/bengkel (`[('state', '!=', 'maintenance')]`).
  - Terindeks (`index=True`) dan tidak disalin saat duplikasi dokumen (`copy=False`).
- `driver_id` (Many2one -> `res.partner`):
  - Label: `"Driver"`
  - Domain penyaringan: hanya menampilkan entitas kontak perorangan (`[('is_company', '=', False)]`).
  - Tidak disalin saat duplikasi dokumen (`copy=False`).
- Otomatisasi Onchange (`@api.onchange('vehicle_id')`):
  - Saat pengguna memilih `vehicle_id` pada form `stock.picking`, jika armada tersebut memiliki data supir penanggung jawab (`vehicle_id.driver_id`), sistem secara otomatis mengisi nilai field `driver_id`.
  - Dispatcher tetap diperkenankan mengganti `driver_id` secara manual apabila terjadi pergantian supir bertugas (*shift/substitute*).

#### Scenario: Penugasan Armada Kendaraan dan Otomatisasi Supir Bertugas (Happy Path)
- **GIVEN** dokumen Delivery Order (`stock.picking` bertipe `outgoing`) dan armada kendaraan `B 1234 WMS` yang telah memiliki supir tetap `Budi Santoso`
- **WHEN** staf logistik memilih armada `B 1234 WMS` pada formulir pengantaran
- **THEN** sistem secara otomatis mengisi nilai field `driver_id` dengan `Budi Santoso` dan menyimpan relasi tersebut saat formulir disimpan

#### Scenario: Penggantian Supir Pengantar Secara Manual oleh Dispatcher (Happy Path)
- **GIVEN** dokumen Delivery Order dengan armada `B 1234 WMS` dan supir terisi otomatis `Budi Santoso`
- **WHEN** staf logistik mengubah supir pengantar menjadi supir pengganti `Ahmad Hidayat`
- **THEN** sistem menerima pembaruan tersebut dan menyimpan `driver_id = Ahmad Hidayat` tanpa mengubah supir tetap pada master `wms.vehicle`

### Requirement: [REQ-OUT-05] Komputasi Otomatis Total Berat dan Volume Muatan serta Validasi Kapasitas Armada
The system MUST menghitung akumulasi total berat (`total_weight`) dan total volume kubikasi kargo (`total_volume`) secara otomatis dari seluruh baris pergerakan stok (`move_ids`), serta memvalidasi kesesuaian kapasitas muatan terhadap armada kendaraan yang ditugaskan.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Spesifikasi kalkulasi dan atribut terkomputasi:
- `total_weight` (Float, Read-only):
  - Label: `"Total Weight (kg)"`
  - Formula: $\sum (\text{move.product\_uom\_qty} \times \text{move.product\_id.weight})$ untuk seluruh `move_ids` yang tidak berstatus dibatalkan (`cancel`).
  - Bergantung pada `@api.depends('move_ids.product_uom_qty', 'move_ids.product_id.weight', 'move_ids.state')` dan tersimpan di database (`store=True`).
- `total_volume` (Float, Read-only):
  - Label: `"Total Volume (m³)"`
  - Formula: $\sum (\text{move.product\_uom\_qty} \times \text{move.product\_id.volume})$ untuk seluruh `move_ids` yang tidak berstatus dibatalkan (`cancel`).
  - Bergantung pada `@api.depends('move_ids.product_uom_qty', 'move_ids.product_id.volume', 'move_ids.state')` dan tersimpan di database (`store=True`).
- Validasi Batasan Kapasitas Muatan (*Capacity Validation Constraint*):
  - Method validasi `@api.constrains('vehicle_id', 'total_weight', 'total_volume')`.
  - Jika `vehicle_id` ditetapkan dan `vehicle_id.max_weight > 0` serta `total_weight > vehicle_id.max_weight`:
    - Sistem memicu `ValidationError` yang menyatakan bahwa muatan kargo melebihi batas berat maksimum kendaraan.
  - Jika `vehicle_id` ditetapkan dan `vehicle_id.max_volume > 0` serta `total_volume > vehicle_id.max_volume`:
    - Sistem memicu `ValidationError` yang menyatakan bahwa muatan kargo melebihi batas volume kubikasi maksimum kendaraan.

#### Scenario: Komputasi Akumulasi Total Berat dan Volume Muatan (Happy Path)
- **GIVEN** dokumen Delivery Order dengan 2 baris kargo:
  - 10 unit Kopi (berat 0.5 kg/unit, volume 0.02 m³/unit)
  - 20 unit Teh (berat 0.25 kg/unit, volume 0.01 m³/unit)
- **WHEN** baris barang disimpan pada dokumen transfer
- **THEN** sistem secara otomatis menghitung `total_weight = 10.0 kg` dan `total_volume = 0.4 m³`

#### Scenario: Penolakan Validasi Dokumen Saat Muatan Melebihi Kapasitas Kendaraan (Edge Case)
- **GIVEN** dokumen Delivery Order dengan akumulasi `total_weight = 3000.0 kg`
- **WHEN** pengguna mencoba menetapkan armada kendaraan dengan `max_weight = 2000.0 kg` dan menyimpan dokumen
- **THEN** sistem menolak penyimpanan dan memunculkan `ValidationError` yang menerangkan bahwa muatan melebihi kapasitas maksimum armada

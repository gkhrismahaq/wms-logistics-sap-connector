# Specification: Master Data API Connector

## Purpose
Menyediakan antarmuka REST API JSON `/api/sap/master` yang aman, idempoten, dan teraudit untuk menerima pembaruan master data Material (Produk), Mitra Rekanan (Vendor dan Customer), serta data Plant dari sistem SAP Upper Line ke WMS Odoo 17.

## Requirements

### Requirement: [REQ-MDAPI-01] Otentikasi dan Keamanan Endpoint REST API Master Data
The system MUST memvalidasi setiap permintaan HTTP yang masuk ke endpoint `/api/sap/master` menggunakan token rahasia yang dikirimkan melalui header `X-Odoo-API-Key` atau `Authorization: Bearer <token>`, dan memverifikasinya terhadap parameter konfigurasi `wms_sap_connector.sap_api_token`.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.5.1

Spesifikasi teknis otentikasi:
- Jika token otentikasi valid, sistem MUST melanjutkan pemrosesan payload.
- Jika token otentikasi tidak disertakan atau tidak cocok, sistem MUST menolak permintaan dengan status HTTP 401 Unauthorized dan mengembalikan pesan galat JSON standar tanpa memproses data apa pun.

#### Scenario: Akses API Berhasil Menggunakan Token Valid
- **GIVEN** server Odoo telah mengonfigurasi parameter token `wms_sap_connector.sap_api_token`
- **WHEN** sistem SAP mengirimkan HTTP POST ke `/api/sap/master` dengan header `X-Odoo-API-Key` yang sesuai
- **THEN** sistem mengotorisasi permintaan dan melanjutkan ke tahap pemrosesan data master

#### Scenario: Penolakan Akses API dengan Token Tidak Valid
- **GIVEN** server Odoo telah mengonfigurasi parameter token otentikasi
- **WHEN** klien eksternal mengirimkan HTTP POST ke `/api/sap/master` tanpa token atau dengan token salah
- **THEN** sistem segera mengembalikan respons penolakan HTTP 401 dengan struktur JSON `{ "status": "ERROR", "code": 401, "message": "Unauthorized: Invalid or missing API token" }`

### Requirement: [REQ-MDAPI-02] Sinkronisasi Idempoten Master Data Material Produk dengan Penanganan Gambar Base64
The system MUST memproses payload data master material produk (`master_type == 'product'`) secara idempoten (*upsert*), mencocokkan record berdasarkan atribut `sap_material_code`, serta mengonversi string gambar Base64 menjadi file biner visual produk pada field `image_1920`.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.1, 3.2, 3.5.1

Spesifikasi teknis pemrosesan material:
- Atribut yang didukung: `sap_material_code` (Wajib, String unik), `name` (Wajib, String), `weight` (Float, kg), `volume` (Float, m³), `image_1920` / `image_base64` (Opsional, String Base64), `barcode` (Opsional, String).
- Perilaku *Upsert*: Jika produk dengan `sap_material_code` tersebut sudah ada di `product.template`, sistem MUST memperbarui (*update*) data yang ada. Jika belum ada, sistem MUST membuat (*create*) record baru.
- Penanganan gambar: Jika parameter gambar Base64 valid disertakan, sistem MUST menyimpannya langsung ke field bawaan Odoo `image_1920`. Jika string Base64 rusak atau tidak valid, sistem MUST mengabaikan gambar tanpa membatalkan pembuatan record data teks lainnya.

#### Scenario: Pembuatan Produk Baru dari Payload SAP
- **GIVEN** sebuah kode material SAP `MAT-SUSU-01` belum terdaftar pada sistem Odoo
- **WHEN** endpoint `/api/sap/master` menerima payload material `MAT-SUSU-01` lengkap dengan nama, berat, volume, dan string Base64 gambar
- **THEN** sistem membuat record `product.template` baru dengan field `sap_material_code = 'MAT-SUSU-01'`, menyimpan foto visual ke `image_1920`, dan mengembalikan status sukses

#### Scenario: Pembaruan Data Produk Eksisting (Idempoten)
- **GIVEN** produk dengan `sap_material_code = 'MAT-SUSU-01'` sudah ada di database Odoo
- **WHEN** endpoint menerima pembaruan informasi berat dan nama untuk material tersebut
- **THEN** sistem memperbarui record yang ada tanpa menciptakan record duplikat, dan mengembalikan respon konfirmasi berhasil

### Requirement: [REQ-MDAPI-03] Sinkronisasi Idempoten Master Data Mitra Rekanan Bisnis (Vendor & Customer)
The system MUST memproses payload data master mitra bisnis (`master_type == 'partner'`) secara idempoten (*upsert*), mencocokkan entitas berdasarkan field `sap_partner_code`, dan mengklasifikasikan tipe mitra (`vendor` atau `customer`) secara presisi.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.1, 3.2, 3.5.1

Spesifikasi teknis pemrosesan mitra:
- Atribut yang didukung: `sap_partner_code` (Wajib, String unik), `name` (Wajib, String), `partner_type` (Pilihan: `vendor` atau `customer`), `street` (Opsional), `city` (Opsional), `phone` (Opsional).
- Aturan klasifikasi:
  - Jika `partner_type == 'vendor'`, sistem MUST menetapkan `supplier_rank = 1`.
  - Jika `partner_type == 'customer'`, sistem MUST menetapkan `customer_rank = 1`.
- Perilaku *Upsert*: Jika rekanan dengan `sap_partner_code` telah ada pada `res.partner`, sistem memperbarui data. Jika belum ada, sistem membuat record baru.

#### Scenario: Sinkronisasi Mitra Vendor Baru dari SAP
- **GIVEN** kode rekanan SAP `VEND-UNILEVER-01` belum ada di sistem Odoo
- **WHEN** endpoint `/api/sap/master` menerima payload rekanan dengan `partner_type = 'vendor'`
- **THEN** sistem membuat record `res.partner` baru dengan `sap_partner_code = 'VEND-UNILEVER-01'` dan `supplier_rank = 1`

#### Scenario: Sinkronisasi Mitra Customer Baru dari SAP
- **GIVEN** kode rekanan SAP `CUST-TOKO-01` belum ada di sistem Odoo
- **WHEN** endpoint `/api/sap/master` menerima payload rekanan dengan `partner_type = 'customer'`
- **THEN** sistem membuat record `res.partner` baru dengan `sap_partner_code = 'CUST-TOKO-01'` dan `customer_rank = 1`

### Requirement: [REQ-MDAPI-04] Pencatatan Transaksi Sinkronisasi Otomatis ke Audit Log
The system MUST secara otomatis mencatat setiap transaksi pertukaran data yang diterima oleh endpoint `/api/sap/master` ke dalam model `sap.sync.log` dengan menyertakan payload JSON lengkap, arah transaksi `inbound`, serta status eksekusi `success` atau `failed`.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2, 3.5.1

Spesifikasi teknis audit log:
- Field yang wajib terisi:
  - `name`: Nomor referensi transaksi sinkronisasi (berformat `SYNC-MD-{YYYYMMDD}-{INDEX/UUID}`).
  - `sync_type`: Disetel ke `master_product` atau `master_partner`.
  - `direction`: Disetel ke `inbound`.
  - `payload`: Salinan string JSON lengkap dari request yang diterima.
  - `status`: Bernilai `success` jika transaksi berhasil, atau `failed` jika terjadi kegagalan pemrosesan.
  - `error_message`: Deskripsi rinci pesan kesalahan jika status bernilai `failed`.

#### Scenario: Pencatatan Log Sukses Saat Sinkronisasi Berhasil
- **GIVEN** sistem menerima request master data yang valid dan berhasil memprosesnya
- **WHEN** seluruh record berhasil disimpan ke database
- **THEN** sistem membuat record pada `sap.sync.log` dengan status `success` dan salinan payload JSON asli

#### Scenario: Pencatatan Log Galat Saat Format Data Invalid
- **GIVEN** sistem menerima request master data dengan struktur JSON tidak valid atau field wajib kosong
- **WHEN** pemrosesan menghasilkan eksepsi
- **THEN** sistem membuat record pada `sap.sync.log` dengan status `failed` lengkap dengan rincian galat pada `error_message`, serta mengembalikan respons HTTP galat ke klien

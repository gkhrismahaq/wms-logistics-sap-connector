# Design Document: API Receive SAP Master Data

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | api-receive-sap-master-data                   |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `product.template`, `res.partner`, `sap.sync.log`, `res.config.settings` |

## Context
Pada integrasi Two-Tier ERP, sistem SAP Upper Line mengelola ribuan data master material produk, vendor, dan pelanggan pusat. Pada tahapan sebelumnya, model data WMS Odoo 17 telah diperluas dengan field referensi SAP (`sap_material_code` pada `product.template`, `sap_partner_code` pada `res.partner`, dan audit log `sap.sync.log`). Konfigurasi token otentikasi `sap_api_token` juga telah tersedia pada `res.config.settings`.

Langkah selanjutnya adalah membangun antarmuka controller HTTP REST API resmi `/api/sap/master` yang mampu menerima instruksi sinkronisasi data master dari SAP, mengotentikasi request menggunakan token API, menjalankan operasi *upsert* idempoten, mengonversi gambar Base64 menjadi foto produk, dan mendokumentasikan setiap transaksi ke dalam tabel audit log.

## Goals / Non-Goals
### Goals
- Mengimplementasikan Odoo Controller pada `addons/wms_sap_connector/controllers/main.py` dengan rute `POST /api/sap/master` bertipe JSON.
- Menerapkan pengamanan otentikasi header `X-Odoo-API-Key` atau `Authorization: Bearer <token>` yang divalidasi terhadap parameter sistem `wms_sap_connector.sap_api_token`.
- Menerapkan mekanisme *idempotent upsert* untuk material produk dan mitra bisnis berdasarkan kode unik SAP.
- Menerapkan konversi aman string gambar Base64 ke biner `image_1920` Odoo.
- Merekam setiap payload masuk beserta status hasil pemrosesan (`success` atau `failed`) ke dalam model `sap.sync.log`.
- Mengembalikan response JSON standar yang informatif dengan status kode HTTP yang sesuai (200 OK, 400 Bad Request, 401 Unauthorized).

### Non-Goals
- Tidak mengimplementasikan endpoint transaksi dokumen operasional seperti Purchase Order (`/api/sap/inbound/po`) atau Delivery Order (`/api/sap/outbound/delivery`) pada change ini (hal tersebut merupakan ruang lingkup Fase 3 dan Fase 4).
- Tidak mengimplementasikan transmisi webhook keluar (*outbound*) dari Odoo ke SAP pada change ini.
- Tidak mengubah skema tabel database model produk atau partner yang telah diarsip pada change sebelumnya.

## Decisions (ADR)
### 1. Penggunaan Odoo Native Controller (http.Controller) dengan Rute JSON
- **Rationale:** Odoo 17 menyediakan dekorator `@http.route` dengan parameter `type='json'` dan `auth='public'` yang menangani parsing payload JSON secara otomatis dan efisien tanpa memerlukan dependensi library pihak ketiga.
- **Alternatives Considered:** Menggunakan REST framework eksternal seperti Flask/FastAPI di dalam container Odoo atau XML-RPC bawaan Odoo. Opsi ini ditolak karena menambah overhead arsitektur dan mempersulit pemeliharaan modul standar Odoo.
- **Consequences:** Endpoint `/api/sap/master` terintegrasi langsung dalam siklus hidup web server Odoo dan dapat langsung mengakses ORM environment (`request.env`).

### 2. Validasi Keamanan Token Header Berbasis Parameter Sistem
- **Rationale:** Mengamankan endpoint publik menggunakan token rahasia yang disimpan dalam parameter sistem `wms_sap_connector.sap_api_token`. Request memeriksa header `X-Odoo-API-Key` atau header standar HTTP `Authorization: Bearer <token>`.
- **Alternatives Considered:** Menggunakan autentikasi sesi berbasis cookie atau login pengguna Odoo (`auth='user'`). Pendekatan ini ditolak karena integrasi machine-to-machine (M2M) dari SAP/middleware membutuhkan otentikasi stateless berbasis token.
- **Consequences:** Klien eksternal wajib menyertakan token API yang valid pada setiap HTTP header request.

### 3. Pola Idempotent Upsert Berbasis Search ORM dengan Indeks B-Tree
- **Rationale:** Dalam pertukaran data terdistribusi, risiko pengiriman ulang payload (*retry*) sangat tinggi. Dengan mencari record terlebih dahulu berdasarkan `sap_material_code` atau `sap_partner_code` yang telah diindeks B-Tree ($O(\log n)$), sistem dapat memutuskan secara instan apakah harus melakukan pembaruan (`write`) atau pembuatan record baru (`create`), sehingga tidak akan pernah terjadi data ganda.
- **Alternatives Considered:** Langsung melakukan `create` dan menangkap *unique constraint exception*. Pendekatan ini ditolak karena Odoo ORM membatalkan seluruh transaksi PostgreSQL (*subtransaction rollback*) saat terjadi error basis data level rendah.
- **Consequences:** Operasi sinkronisasi menjadi sangat aman, stabil, dan dapat diulang berkali-kali tanpa efek samping (*idempotent*).

### 4. Isolasi Pencatatan Log pada sap.sync.log
- **Rationale:** Setiap request, baik yang berhasil maupun yang menghasilkan galat, wajib tercatat ke `sap.sync.log`. Untuk mencegah pembatalan log saat terjadi error pada pemrosesan record, pencatatan log dijalankan dalam penanganan eksepsi `try...finally` atau `try...except` sehingga log transaksi gagal tetap tersimpan di database.
- **Alternatives Considered:** Hanya mencatat log jika transaksi berhasil. Opsi ini ditolak karena bertentangan dengan prinsip auditabilitas sistem enterprise (SSOT tsd.md Bagian 3.2).
- **Consequences:** Tim operasional dapat meninjau riwayat transaksi yang gagal langsung melalui antarmuka Odoo UI "SAP Integration Logs" dan menekan tombol "Retry Sync".

## Technical Architecture & Data Schema
### Kontrak Request JSON Endpoint (`POST /api/sap/master`)

#### Payload Master Material / Produk:
```json
{
  "master_type": "product",
  "data": [
    {
      "sap_material_code": "MAT-KOPI-01",
      "name": "Kopi Kapal Api Special 65g",
      "weight": 0.065,
      "volume": 0.0001,
      "barcode": "899100100101",
      "image_base64": "/9j/4AAQSkZJRgABAQEASABIAAD/..."
    }
  ]
}
```

#### Payload Master Rekanan Bisnis (Vendor / Customer):
```json
{
  "master_type": "partner",
  "data": [
    {
      "sap_partner_code": "VEND-INDOMARCO",
      "name": "PT Indomarco Prismatama",
      "partner_type": "vendor",
      "street": "Jl. Ancol Barat No. 9",
      "city": "Jakarta Utara",
      "phone": "+62 21 6901234"
    }
  ]
}
```

### Kontrak Respon JSON

#### Respon Sukses (200 OK):
```json
{
  "status": "SUCCESS",
  "code": 200,
  "message": "Master data processed successfully",
  "sync_ref": "SYNC-MD-20261026-0001",
  "processed_count": 1
}
```

#### Respon Galat Otorisasi (401 Unauthorized):
```json
{
  "status": "ERROR",
  "code": 401,
  "message": "Unauthorized: Invalid or missing API token"
}
```

#### Respon Galat Validasi (400 Bad Request):
```json
{
  "status": "ERROR",
  "code": 400,
  "message": "Bad Request: Missing 'master_type' or empty 'data' payload"
}
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| String Base64 gambar sangat besar membebani memori server | Medium | Validasi string Base64 sebelum konversi; jika format tidak valid atau gagal didecode, abaikan gambar dan log peringatan tanpa menggagalkan data produk. |
| Payload JSON dikirim tanpa parameter wajib | Medium | Validasi skema ketat di awal controller; kembalikan pesan galat 400 terperinci dan rekam ke `sap.sync.log` dengan status `failed`. |
| Akses API tidak sah dari luar jaringan | High | Proteksi ketat via token API (`X-Odoo-API-Key` / Bearer token) yang dicocokkan dengan parameter sistem terenkripsi. |
| Konflik konkurensi saat multi-request bersamaan | Low | Menggunakan ORM `search` dengan parameter pencocokan terindeks B-Tree pada basis data PostgreSQL. |

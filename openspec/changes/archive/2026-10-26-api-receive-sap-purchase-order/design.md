# Design Document: API Receive SAP Purchase Order

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | api-receive-sap-purchase-order                |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `stock.picking`, `stock.move`, `res.partner`, `product.product`, `sap.sync.log` |

## Context
Pada arsitektur Two-Tier ERP, pesanan pembelian (*Purchase Order*) dibuat dan dikelola di SAP Upper Line. Pada perubahan sebelumnya (`extend-picking-inbound-fields`), model `stock.picking` telah disiapkan dengan field `sap_doc_number` dan `sap_sync_status`. Master data produk/material dan rekanan/vendor juga telah tersedia dan terpetakan dengan kode unik SAP.

Langkah berikutnya adalah membangun endpoint REST API JSON `POST /api/sap/inbound/po` yang memungkinkan sistem SAP atau simulator middleware mengirimkan instruksi pesanan pembelian ke WMS Odoo 17, memvalidasi vendor dan material, serta secara otomatis menerbitkan dokumen penerimaan barang (*Stock Picking Receipts*) dan baris mutasi stok (*Stock Move*) dengan status siap terima (*assigned* / Ready).

## Goals / Non-Goals
### Goals
- Mengimplementasikan endpoint REST API `POST /api/sap/inbound/po` pada `addons/wms_sap_connector/controllers/main.py`.
- Memvalidasi otentikasi request menggunakan token API (`X-Odoo-API-Key` atau `Authorization: Bearer <token>`) terhadap parameter `wms_sap_connector.sap_api_token`.
- Menerapkan mekanisme *idempotent creation* berbasis `sap_doc_number` untuk mencegah timbulnya dokumen picking ganda saat terjadi transmisi ulang (*retry*).
- Memetakan kode rekanan SAP (`vendor_code`) ke model `res.partner` dan kode material SAP (`sap_material_code`) ke model `product.product`.
- Membuat dokumen `stock.picking` bertipe operasi `incoming` (Receipts) beserta baris `stock.move` untuk setiap item pesanan.
- Menjalankan method `action_confirm()` pada picking agar dokumen bertransisi otomatis ke status `assigned` (Ready).
- Mencatat seluruh jejak audit transaksi (sukses maupun gagal) ke dalam model `sap.sync.log` dengan tipe `inbound_po`.
- Mengembalikan respons JSON terstruktur dengan HTTP status 201 Created (sukses) atau kode error yang tepat (400, 401).

### Non-Goals
- Tidak mengimplementasikan pengiriman sinyal webhook konfirmasi Goods Receipt dari Odoo ke SAP pada change ini (hal ini merupakan ruang lingkup change `webhook-notify-sap-goods-receipt`).
- Tidak mengimplementasikan algoritma penempatan rak otomatis (*Putaway Rule*) pada change ini (hal ini merupakan ruang lingkup change `automate-putaway-bin-allocation`).
- Tidak mengubah skema tabel database model `stock.picking` yang telah diarsip pada change sebelumnya.

## Decisions (ADR)
### 1. Penambahan Rute Inbound PO pada Controller Eksisting (`main.py`)
- **Rationale:** Modul controller `addons/wms_sap_connector/controllers/main.py` telah memiliki fondasi otentikasi stateless (`_authenticate_request()`), pencatatan audit log (`_log_transaction()`), dan pembuatan respons REST JSON (`request.make_json_response()`). Menambahkan rute `/api/sap/inbound/po` pada file ini mencegah redundansi kode helper dan menjaga modularitas Clean Architecture.
- **Alternatives Considered:** Membuat controller baru `controllers/inbound.py`. Opsi ini dihindari untuk menjaga kesederhanaan modul pada fase integrasi saat ini.
- **Consequences:** Seluruh logika integrasi REST API inbound SAP terpusat secara kohesif.

### 2. Idempotensi Berbasis Pencarian `sap_doc_number`
- **Rationale:** Dalam integrasi Two-Tier ERP terdistribusi, pengiriman ulang request PO dari SAP sangat sering terjadi akibat timeout jaringan atau proses retry. Controller memeriksa keberadaan dokumen `stock.picking` berdasarkan `sap_doc_number`. Jika dokumen ditemukan dan statusnya bukan `cancel`, sistem langsung mengembalikan status dokumen yang ada tanpa membuat record baru.
- **Alternatives Considered:** Langsung membuat record dan mengabaikan duplikasi nomor PO. Opsi ini ditolak keras karena menyebabkan stok ganda (*double inventory*) di gudang fisik.
- **Consequences:** Menjamin akurasi 100% data pesanan masuk tanpa risiko redundansi.

### 3. Otomatisasi Pembuatan Baris Stock Move & Transisi Status ke `assigned`
- **Rationale:** Dokumen picking yang dibuat melalui API harus langsung siap diproses oleh staf gudang di area bongkar muat (*docking*). Dengan membuat record `stock.move` yang mereferensikan `picking_id` lalu memanggil method standar Odoo `action_confirm()`, sistem otomatis memesan alur penerimaan dan memindahkan state picking dari `draft` ke `assigned` (Ready).
- **Alternatives Considered:** Membiarkan dokumen picking berstatus `draft`. Opsi ini ditolak karena mewajibkan staf gudang melakukan klik manual "Mark as Todo" di UI Odoo sebelum barang bisa dicek/diterima.
- **Consequences:** Dokumen picking langsung berstatus *Ready* di layar pemindai barcode / tablet staf gudang.

### 4. Resolusi Gudang Tujuan (Multi-Warehouse / Multi-Company)
- **Rationale:** Sistem mendukung 2 gudang: DC Lowokwaru (`DCLOW` / Plant 2100) dan DC Tompokersan (`DCTOM` / Plant 2200). Payload dapat menyertakan `warehouse_code` atau `plant_code` opsional. Jika disertakan, sistem memilih tipe operasi penerimaan gudang bersangkutan. Jika tidak disertakan, sistem default ke tipe operasi penerimaan gudang utama DC Lowokwaru.
- **Alternatives Considered:** Membatasi hanya untuk satu gudang tunggal. Opsi ini ditolak karena operasional Madura Mart mencakup DC Lowokwaru dan DC Tompokersan (SSOT tsd.md Bagian 1.2).
- **Consequences:** Mendukung multi-warehouse secara fleksibel dan skalabel.

## Technical Architecture & Data Schema

### Kontrak Request JSON Endpoint (`POST /api/sap/inbound/po`)
```json
{
  "sap_doc_number": "PO-SAP-2026-001",
  "vendor_code": "VEND-INDOMARCO",
  "expected_date": "2026-10-25",
  "warehouse_code": "DCLOW",
  "items": [
    {
      "sap_material_code": "MAT-KOPI-01",
      "qty": 100.0,
      "uom": "Box"
    }
  ]
}
```

### Kontrak Respons JSON

#### Respons Sukses (201 Created):
```json
{
  "status": "SUCCESS",
  "code": 201,
  "odoo_picking_id": 14,
  "sap_doc_number": "PO-SAP-2026-001",
  "state": "assigned",
  "sync_ref": "SYNC-PO-20261026-A1B2C3"
}
```

#### Respons Idempoten Dokumen Sudah Ada (200 OK):
```json
{
  "status": "SUCCESS",
  "code": 200,
  "message": "Purchase order document already exists (idempotent)",
  "odoo_picking_id": 14,
  "sap_doc_number": "PO-SAP-2026-001",
  "state": "assigned",
  "sync_ref": "SYNC-PO-20261026-D4E5F6"
}
```

#### Respons Galat Otorisasi (401 Unauthorized):
```json
{
  "status": "ERROR",
  "code": 401,
  "message": "Unauthorized: Invalid or missing API token"
}
```

#### Respons Galat Validasi (400 Bad Request):
```json
{
  "status": "ERROR",
  "code": 400,
  "message": "Bad Request: Vendor with SAP partner code 'VEND-XXX' not found"
}
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Vendor SAP belum terdaftar di tabel `res.partner` | Medium | Validasi keberadaan vendor sebelum membuat dokumen; kembalikan HTTP 400 Bad Request informatif dan log kegagalan ke `sap.sync.log`. |
| Material SAP belum terdaftar di tabel `product.template` / `product.product` | Medium | Validasi setiap material dalam array `items`; jika ada yang tidak ditemukan, batalkan transaksi (*rollback*) dan kembalikan pesan galat spesifik. |
| Format tanggal `expected_date` tidak valid | Low | Lakukan parsing tanggal dengan blok `try...except`; gunakan `datetime.now()` sebagai *fallback* aman jika parsing tanggal gagal. |
| Eksepsi internal ORM saat pemanggilan `action_confirm()` | Medium | Seluruh pembuatan picking dan move dibungkus blok transaksi `try...except`, dan setiap kegagalan dicatat ke `sap.sync.log`. |

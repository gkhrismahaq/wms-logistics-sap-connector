# Specification: Inbound Goods Receipt

## ADDED Requirements

### Requirement: [REQ-INB-03] Otentikasi dan Endpoint REST API Penerimaan Inbound Purchase Order
The system MUST menyediakan endpoint REST API JSON `POST /api/sap/inbound/po` yang terotentikasi dan memvalidasi setiap permintaan HTTP menggunakan token rahasia yang dikirimkan melalui header `X-Odoo-API-Key` atau `Authorization: Bearer <token>` terhadap parameter konfigurasi `wms_sap_connector.sap_api_token`.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.5.1, 3.5.2

Spesifikasi teknis otentikasi:
- Jika token otentikasi valid, sistem MUST melanjutkan ke tahap parsing payload dan pemrosesan pesanan pembelian.
- Jika token tidak disertakan atau salah, sistem MUST segera menolak permintaan dengan status HTTP 401 Unauthorized dan format JSON `{ "status": "ERROR", "code": 401, "message": "Unauthorized: Invalid or missing API token" }`.

#### Scenario: Akses API Inbound PO Berhasil Menggunakan Token Valid
- **GIVEN** server Odoo telah mengonfigurasi parameter token `wms_sap_connector.sap_api_token`
- **WHEN** sistem SAP mengirimkan HTTP POST ke `/api/sap/inbound/po` dengan header `X-Odoo-API-Key` yang sesuai
- **THEN** sistem mengotorisasi permintaan dan melanjutkan ke tahap pemrosesan pesanan pembelian

#### Scenario: Penolakan Akses API Inbound PO dengan Token Tidak Valid
- **GIVEN** server Odoo telah mengonfigurasi parameter token otentikasi
- **WHEN** klien eksternal mengirimkan HTTP POST ke `/api/sap/inbound/po` tanpa token atau dengan token salah
- **THEN** sistem segera menolak permintaan dengan status respons HTTP 401 Unauthorized

### Requirement: [REQ-INB-04] Idempotensi dan Otomatisasi Pembuatan Dokumen Stock Picking Inbound dan Stock Move
The system MUST memproses payload pesanan pembelian dari SAP secara idempoten berdasarkan atribut `sap_doc_number`, memvalidasi mitra vendor (`res.partner`) berdasarkan `vendor_code`, memetakan item barang (`product.product`) berdasarkan `sap_material_code`, serta secara otomatis menerbitkan dokumen `stock.picking` bertipe operasi `incoming` beserta baris perpindahan stok `stock.move` dengan status siap proses (`assigned` / Ready).
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.2, 3.5.2

Spesifikasi teknis pemrosesan dokumen:
- Atribut payload yang didukung:
  - `sap_doc_number` (Wajib, String unik): Nomor referensi dokumen PO SAP (contoh: `PO-SAP-2026-001`).
  - `vendor_code` (Wajib, String): Kode rekanan SAP vendor pemasok barang (dicocokkan ke `res.partner.sap_partner_code`).
  - `expected_date` (Opsional, String tanggal YYYY-MM-DD): Estimasi tanggal barang tiba di gudang.
  - `warehouse_code` / `plant_code` (Opsional, String): Kode gudang tujuan atau plant penampung stok (default ke gudang utama DC Lowokwaru jika tidak disertakan).
  - `items` (Wajib, Array of Objects): Daftar item pesanan pembelian. Tiap item memuat `sap_material_code` (Wajib, String) dan `qty` (Wajib, Float > 0).
- Penanganan Idempoten:
  - Jika dokumen `stock.picking` dengan `sap_doc_number` tersebut telah ada di database dan belum dibatalkan, sistem MUST mengembalikan detail dokumen yang telah ada tanpa membuat duplikat (*idempotent*).
- Otomatisasi Status Dokumen:
  - Dokumen baru dibuat dengan `picking_type_id.code == 'incoming'`, `location_id` lokasi supplier (`stock.stock_location_suppliers`), dan `location_dest_id` lokasi gudang persediaan fisik.
  - Untuk setiap item pada array `items`, sistem membuat record `stock.move` terkait.
  - Dokumen dikonfirmasi otomatis (`action_confirm()`) sehingga status berpindah dari `draft` ke `assigned` (Ready untuk penerimaan fisik).
  - Sistem mengembalikan respons HTTP 201 Created dengan format `{ "status": "SUCCESS", "code": 201, "odoo_picking_id": <id>, "sap_doc_number": "<no>", "state": "assigned" }`.

#### Scenario: Pembuatan Dokumen Picking Inbound Baru dari Payload SAP PO
- **GIVEN** kode dokumen PO SAP `PO-SAP-2026-001`, vendor `VEND-INDOMARCO`, dan material `MAT-KOPI-01` telah terdaftar di database
- **WHEN** endpoint `/api/sap/inbound/po` menerima request payload PO valid
- **THEN** sistem membuat record `stock.picking` baru dengan `sap_doc_number = 'PO-SAP-2026-001'`, membuat baris `stock.move`, mengonfirmasi status menjadi `assigned`, dan mengembalikan respons HTTP 201 Created

#### Scenario: Permintaan Ulang Dokumen PO yang Sama Menghasilkan Respon Idempoten
- **GIVEN** dokumen penerimaan untuk `PO-SAP-2026-001` telah berhasil dibuat sebelumnya
- **WHEN** endpoint `/api/sap/inbound/po` menerima kembali payload dengan nomor dokumen `PO-SAP-2026-001` yang sama
- **THEN** sistem tidak menciptakan record picking duplikat, dan mengembalikan referensi ID dokumen picking yang sudah ada beserta status terkini

#### Scenario: Penolakan Request Saat Vendor Code atau Material Code SAP Tidak Ditemukan
- **GIVEN** sebuah payload PO dikirim dengan kode vendor atau kode material yang tidak terdaftar di sistem Odoo
- **WHEN** endpoint `/api/sap/inbound/po` memvalidasi master data
- **THEN** sistem membatalkan pembuatan transaksi, mengembalikan respons HTTP 400 Bad Request dengan rincian galat yang jelas, dan mencatat transaksi gagal ke audit log

### Requirement: [REQ-INB-05] Pencatatan Transaksi Inbound PO ke Audit Log Integrasi
The system MUST secara otomatis mendokumentasikan setiap request yang diterima oleh endpoint `/api/sap/inbound/po` ke dalam model `sap.sync.log` dengan menyertakan payload JSON lengkap, arah transaksi `inbound`, tipe sinkronisasi `inbound_po`, serta status eksekusi `success` atau `failed`.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2, 3.5.2

Spesifikasi teknis audit log:
- Field yang wajib terisi:
  - `name`: Nomor referensi unik berformat `SYNC-PO-{YYYYMMDD}-{UUID}`.
  - `sync_type`: `inbound_po`.
  - `direction`: `inbound`.
  - `payload`: Salinan string JSON lengkap dari request.
  - `status`: `success` jika dokumen picking berhasil dibuat/diakses, atau `failed` jika terjadi kegagalan pemrosesan.
  - `error_message`: Deskripsi rinci pesan kegagalan jika status bernilai `failed`.

#### Scenario: Pencatatan Audit Log Sukses Saat Inbound PO Berhasil Diterbitkan
- **GIVEN** request pesanan pembelian valid diterima dan berhasil diproses
- **WHEN** dokumen picking dan stock move berhasil disimpan
- **THEN** sistem membuat record pada `sap.sync.log` dengan `sync_type = 'inbound_po'`, status `success`, dan payload JSON asli

#### Scenario: Pencatatan Audit Log Gagal Saat Terjadi Validasi Error atau Data Kurang
- **GIVEN** request pesanan pembelian dikirim dengan parameter wajib kosong atau vendor tidak valid
- **WHEN** pemrosesan menghasilkan eksepsi
- **THEN** sistem membuat record pada `sap.sync.log` dengan status `failed` lengkap dengan rincian galat pada field `error_message`

## MODIFIED Requirements
None

## REMOVED Requirements
None

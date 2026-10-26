# Specification: Mock SAP Service

## Purpose
Menyediakan server simulator mandiri berbasis framework FastAPI yang mereplikasi endpoint RESTful dan webhook SAP Upper Line secara realistis, lengkap dengan antarmuka Swagger UI interaktif serta simulasi jurnal akuntansi keuangan untuk memvalidasi integrasi Two-Tier ERP Odoo WMS dalam lingkungan pengembangan lokal.

## Requirements

### Requirement: [REQ-MOCK-01] Layanan Mock Server SAP Berbasis FastAPI dan Dokumentasi Interaktif
The system MUST menyediakan server HTTP mandiri berbasis FastAPI (`mock_sap_server.py`) yang mengekspos dokumentasi Swagger UI interaktif pada rute `/docs`, antarmuka ReDoc pada `/redoc`, endpoint healthcheck pada `/health`, serta memvalidasi otorisasi request melalui header `Authorization: Bearer <token>` atau `X-Odoo-API-Key: <token>`.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.5.1

Spesifikasi arsitektur dan endpoint:
- **Konfigurasi Server:**
  - Berjalan secara default pada host `0.0.0.0` dan port `8000` (dapat dikonfigurasi via variabel lingkungan `PORT` / `MOCK_SAP_PORT`).
  - Kredensial otorisasi default `secret_sap_token_123` (dapat dikonfigurasi via variabel lingkungan `SAP_API_TOKEN`).
- **Endpoint Healthcheck:**
  - `GET /health` dan `GET /`: Mengembalikan status HTTP 200 dengan JSON `{"status": "ok", "service": "Mock SAP Service", "version": "1.0.0"}`.
- **Validasi Otorisasi:**
  - Setiap endpoint terproteksi (`/api/sap/*` dan `/api/trigger/*`) wajib memvalidasi token dari header `X-Odoo-API-Key` atau `Authorization: Bearer <token>`.
  - Jika token tidak valid atau tidak disertakan, server MUST menolak permintaan dengan status HTTP 401 Unauthorized `{"status": "ERROR", "code": 401, "message": "Unauthorized: Invalid or missing API token"}`.

#### Scenario: Akses Dokumentasi Swagger UI dan Healthcheck (Happy Path)
- **GIVEN** server mock SAP sedang berjalan pada port 8000
- **WHEN** pengembang atau staf QA mengakses endpoint `GET /health` atau antarmuka `GET /docs` melalui browser atau HTTP client
- **THEN** server mengembalikan respons status OK 200 dan menyajikan antarmuka visual OpenAPI/Swagger UI interaktif

#### Scenario: Penolakan Permintaan Webhook Tanpa Token Otorisasi (Edge Case)
- **GIVEN** klien mengirimkan permintaan ke rute terproteksi `/api/sap/goods-receipt` tanpa header kredensial otorisasi yang valid
- **WHEN** permintaan diterima oleh middleware otentikasi mock server
- **THEN** server menolak permintaan dengan kode status HTTP 401 Unauthorized dan mengembalikan pesan galat terstruktur

### Requirement: [REQ-MOCK-02] Endpoint Webhook Receiver Goods Receipt dan Goods Issue
The system MUST menyediakan endpoint webhook HTTP POST receiver (`/api/sap/goods-receipt` dan `/api/sap/goods-issue`) yang menampung konfirmasi operasional gudang dari Odoo dan mengembalikan respons simulasi jurnal akuntansi SAP (`sap_accounting_log`) yang sesuai dengan standar akuntansi persediaan.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.5.2 & 3.5.3

Spesifikasi endpoint dan payload:
- **Webhook Goods Receipt (`POST /api/sap/goods-receipt`):**
  - Menerima payload JSON: `sap_doc_number` (String), `status` (`"GOODS_RECEIVED"`), `received_date` (String ISO 8601), dan `warehouse_code` (String).
  - Mengembalikan status HTTP 200 dengan payload:
    ```json
    {
      "status": "SUCCESS",
      "code": 200,
      "message": "Goods Receipt posted into SAP General Ledger",
      "sap_accounting_log": {
        "journal_entry": "JE-SAP-YYYY-XXXX",
        "posting_date": "YYYY-MM-DD",
        "debit_account": "101.001 - Persediaan Barang Masuk (Rp 50.000.000)",
        "credit_account": "201.001 - Hutang Dagang Belum Difakturkan (Rp 50.000.000)",
        "vat_in_11%": "Rp 5.500.000",
        "financial_status": "POSTED"
      }
    }
    ```
- **Webhook Goods Issue & POD (`POST /api/sap/goods-issue`):**
  - Menerima payload JSON: `sap_doc_number` (String), `status` (`"GOODS_ISSUED"`), `issued_date` (String ISO 8601), `receiver_name` (String), dan `has_pod` (Boolean).
  - Mengembalikan status HTTP 200 dengan payload:
    ```json
    {
      "status": "SUCCESS",
      "code": 200,
      "message": "Goods Issue and POD acknowledged in SAP Financials",
      "sap_accounting_log": {
        "journal_entry": "JE-SAP-YYYY-XXXX",
        "posting_date": "YYYY-MM-DD",
        "debit_account": "501.001 - Harga Pokok Penjualan (HPP) (Rp 25.000.000)",
        "credit_account": "101.001 - Persediaan Barang Jadi (Rp 25.000.000)",
        "financial_status": "POSTED"
      }
    }
    ```

#### Scenario: Penerimaan Webhook Goods Receipt dengan Simulasi Jurnal Finansial (Happy Path)
- **GIVEN** Odoo mengirimkan webhook HTTP POST ke `/api/sap/goods-receipt` dengan payload PO valid dan token otorisasi
- **WHEN** server mock SAP memproses permintaan tersebut
- **THEN** server mencatat riwayat transaksi, mengembalikan status HTTP 200 beserta struktur `sap_accounting_log` dengan entri debit persediaan masuk dan kredit hutang dagang

#### Scenario: Penerimaan Webhook Goods Issue dengan Simulasi Jurnal Pemotongan HPP (Happy Path)
- **GIVEN** Odoo mengirimkan webhook HTTP POST ke `/api/sap/goods-issue` dengan data Surat Jalan dan bukti POD lengkap (`has_pod: true`)
- **WHEN** server mock SAP memvalidasi payload
- **THEN** server mengembalikan status HTTP 200 beserta data `sap_accounting_log` dengan entri debit Harga Pokok Penjualan (HPP) dan kredit Persediaan Barang Jadi

### Requirement: [REQ-MOCK-03] Endpoint Trigger Simulasi Transmisi SAP ke Odoo dan Audit History
The system MUST menyediakan antarmuka trigger HTTP POST untuk memicu pengiriman instruksi SAP ke Odoo secara terkendali melalui Swagger UI atau skrip otomatis, serta menyediakan endpoint inspeksi audit `GET /api/sap/history`.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.5.1, 3.5.2, 3.5.3

Spesifikasi endpoint trigger dan riwayat audit:
- **Target URL Odoo:**
  - Ditentukan melalui variabel lingkungan `ODOO_BASE_URL` (default: `http://localhost:8070` atau `http://odoo:8069` di jaringan Docker).
- **Trigger Master Data (`POST /api/trigger/master-data`):**
  - Mengirimkan payload master material atau partner ke endpoint Odoo `POST /api/sap/master`.
- **Trigger Inbound PO (`POST /api/trigger/inbound-po`):**
  - Mengirimkan instruksi pesanan pembelian ke endpoint Odoo `POST /api/sap/inbound/po`.
- **Trigger Outbound Delivery (`POST /api/trigger/outbound-delivery`):**
  - Mengirimkan instruksi pengiriman kargo ke endpoint Odoo `POST /api/sap/outbound/delivery`.
- **Audit History (`GET /api/sap/history`):**
  - Mengembalikan daftar rekaman seluruh webhook yang diterima (`goods_receipt`, `goods_issue`) dan trigger yang dikirim beserta timestamp dan status responsnya.
  - Endpoint `DELETE /api/sap/history` untuk mengosongkan rekaman sebelum pengujian baru dimulai.

#### Scenario: Pemicuan Inbound PO ke Odoo dan Pencatatan Riwayat Transaksi (Happy Path)
- **GIVEN** server Odoo berjalan dan mock SAP dikonfigurasi dengan URL target Odoo yang tepat
- **WHEN** pengguna mengeksekusi `POST /api/trigger/inbound-po` dengan payload PO pesanan pembelian
- **THEN** server mock SAP meneruskan request ke Odoo, menerima respons 201 Created dari Odoo, dan mencatat transaksi ke dalam audit history

#### Scenario: Penanganan Kegagalan Koneksi Target Odoo (Edge Case)
- **GIVEN** target server Odoo sedang offline atau tidak dapat dijangkau
- **WHEN** pengguna mengeksekusi salah satu endpoint pemicu (`/api/trigger/*`)
- **THEN** server mock SAP menangani connection error secara elegan dan mengembalikan status HTTP 502 Bad Gateway beserta rincian kegagalan koneksi

### Requirement: [REQ-MOCK-04] Validasi Integrasi Menyeluruh Dua Arah (End-to-End E2E Testing) Two-Tier WMS dan SAP
The system MUST menyediakan rangkaian pengujian otomatis integrasi end-to-end (E2E) yang memvalidasi siklus penuh aliran data dua arah antara Odoo 17 WMS dan SAP Upper Line Mock Service secara berkesinambungan dan konsisten tanpa intervensi manual.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2, 3.5

Rangkaian alur pengujian E2E mencakup tahapan terpadu:
1. **Tahap 1: Sinkronisasi Master Data:**
   - SAP Mock mentransmisikan data material (termasuk gambar produk dalam format Base64, dimensi berat, volume, barcode) dan data mitra bisnis (Vendor dan Customer) ke endpoint Odoo `POST /api/sap/master`.
   - Sistem Odoo memvalidasi otentikasi token, memproses data secara idempoten ke `product.template` dan `res.partner`, serta mendokumentasikan log transaksi pada `sap.sync.log`.
2. **Tahap 2: Siklus Inbound, Putaway, dan Goods Receipt:**
   - SAP Mock mengirimkan instruksi pesanan pembelian ke Odoo `POST /api/sap/inbound/po`.
   - Odoo menerbitkan dokumen `stock.picking` incoming dengan nomor referensi SAP (`sap_doc_number`) berstatus `assigned`.
   - Sistem menerapkan aturan alokasi rak otomatis (*Putaway Rule*) ke lokasi simpan spesifik sesuai kategori produk.
   - Staf gudang memvalidasi penerimaan fisik barang (`button_validate`), memicu webhook konfirmasi `POST /api/sap/goods-receipt` ke mock server.
   - Odoo menangkap respon simulasi jurnal finansial SAP (`sap_accounting_log` debit persediaan masuk & kredit hutang dagang) dan mencatatnya ke `sap.sync.log` dengan status `success`.
3. **Tahap 3: Siklus Outbound, Dispatch, POD, dan Goods Issue:**
   - SAP Mock mengirimkan instruksi pengiriman kargo ke Odoo `POST /api/sap/outbound/delivery`.
   - Odoo membuat dokumen `stock.picking` outgoing dan menetapkan alokasi armada (`wms.vehicle`) serta supir pengantar.
   - Sistem memvalidasi kapasitas beban muatan armada (berat dan volume) dan menghasilkan laporan cetak Surat Jalan resmi (PDF QWeb).
   - Supir melengkapi berkas digital bukti serah terima (*Proof of Delivery / POD*) berupa foto/tanda tangan penerima (`pod_signed_by`, `pod_timestamp`).
   - Dokumen divalidasi selesai (`button_validate`), memicu webhook `POST /api/sap/goods-issue` ke mock server.
   - Odoo menangkap respon simulasi jurnal pemotongan HPP (`sap_accounting_log`) dan mendokumentasikannya ke `sap.sync.log` dengan status `success`.

#### Scenario: Siklus Lengkap End-to-End Dua Arah Odoo WMS dan SAP Mock Service (Happy Path)
- **GIVEN** seluruh layanan Odoo 17 WMS dan Mock SAP Service aktif dan terhubung dalam satu jaringan
- **WHEN** skenario pengujian integrasi E2E dijalankan dari tahap sinkronisasi master data, alur inbound & putaway, hingga alur outbound, penugasan armada, dan verifikasi bukti POD
- **THEN** seluruh tahapan berhasil dieksekusi dengan kode status HTTP yang sesuai (200/201), status dokumen Odoo bertransisi dengan benar hingga `done`, seluruh webhook terkirim dan diterima secara timbal balik, respon jurnal finansial terekam di `sap.sync.log`, dan riwayat transaksi tercatat lengkap pada mock server

#### Scenario: Penanganan dan Isolasi Kegagalan Jaringan Antar Sistem pada Siklus E2E (Edge Case)
- **GIVEN** terjadi pemutusan konektivitas atau server SAP mock mendadak tidak merespons (timeout) di tengah proses validasi dokumen logistik
- **WHEN** validasi fisik transfer barang diselesaikan di gudang Odoo
- **THEN** transaksi operasional inventori internal Odoo tetap berhasil (`done`) tanpa terpengaruh oleh gangguan sistem eksternal, dokumen ditandai berstatus sinkronisasi `failed`, insiden kegagalan tercatat rapi di `sap.sync.log`, dan tombol aksi pengiriman ulang manual (*Manual Retry*) tersedia bagi pengguna


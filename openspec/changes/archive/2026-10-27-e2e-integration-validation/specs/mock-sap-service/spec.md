# Specification: Mock SAP Service

## ADDED Requirements

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

## MODIFIED Requirements
None

## REMOVED Requirements
None

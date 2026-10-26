# Specification: Inbound SAP Webhook

## Purpose
Menyediakan kemampuan otomasi transmisi sinyal konfirmasi penerimaan fisik barang (*Goods Receipt*) dari WMS Odoo 17 ke sistem SAP Upper Line melalui webhook HTTP POST, serta mendokumentasikan respon jurnal akuntansi SAP ke dalam rekaman audit log sinkronisasi.

## ADDED Requirements

### Requirement: [REQ-WHK-01] Otomatisasi Transmisi Webhook Konfirmasi Goods Receipt ke SAP Saat Validasi Dokumen Selesai
The system MUST secara otomatis mengeksekusi permintaan HTTP POST ke endpoint webhook `{sap_base_url}/api/sap/goods-receipt` sesaat setelah dokumen penerimaan barang (`stock.picking` tipe `incoming`) yang memiliki referensi dokumen SAP (`sap_doc_number`) berhasil divalidasi dan berpindah ke status selesai (`done`).
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.2, 3.5.2

Spesifikasi teknis muatan webhook:
- Header HTTP:
  - `Content-Type: application/json`
  - `Authorization: Bearer <sap_api_token>` (atau `X-Odoo-API-Key: <sap_api_token>`), diambil dari parameter sistem `wms_sap_connector.sap_api_token`.
- Payload JSON:
  - `sap_doc_number` (String, Wajib): Nomor pesanan pembelian SAP yang bersangkutan (contoh: `PO-SAP-2026-001`).
  - `status` (String, Wajib): Nilai konstan `"GOODS_RECEIVED"`.
  - `received_date` (String, Wajib): Waktu penyelesaian dokumen penerimaan dalam format ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`).
  - `warehouse_code` (String, Wajib): Kode gudang tujuan penerimaan fisik dari `picking_type_id.warehouse_id.code` (contoh: `DCLOW`).

#### Scenario: Transmisi Webhook Berhasil Saat Dokumen Receipt Selesai Divalidasi
- **GIVEN** dokumen penerimaan barang masuk berstatus `assigned` dengan nomor SAP `PO-SAP-2026-001`
- **WHEN** staf gudang menekan tombol validasi (`button_validate`) dan dokumen berpindah ke status `done`
- **THEN** sistem secara otomatis mengirimkan payload HTTP POST ke `{sap_base_url}/api/sap/goods-receipt` dan menandai `sap_sync_status = 'synced'` jika SAP mengembalikan status HTTP 200

#### Scenario: Non-Blocking Webhook Failure Saat Layanan SAP Mengalami Gangguan
- **GIVEN** server SAP sedang offline atau koneksi jaringan mengalami *timeout*
- **WHEN** dokumen penerimaan divalidasi hingga berstatus `done`
- **THEN** status transfer fisik stok di gudang Odoo tetap tersimpan sebagai `done` tanpa di-rollback, sistem menandai `sap_sync_status = 'failed'`, dan kegagalan dicatat ke log

### Requirement: [REQ-WHK-02] Pencatatan Respon Jurnal Akuntansi SAP ke Audit Log dan Mekanisme Pengiriman Ulang Manual
The system MUST menangkap seluruh respon balasan dari SAP—termasuk objek simulasi pembukuan jurnal akuntansi persediaan dan hutang dagang (`sap_accounting_log`)—lalu mendokumentasikannya ke tabel `sap.sync.log` dengan arah aliran `outbound`, serta menyediakan tombol aksi pengiriman ulang manual (*Manual Retry*) pada antarmuka formulir picking.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2, 3.5.2

Spesifikasi teknis pencatatan dan retry:
- Audit Log (`sap.sync.log`):
  - `name`: Nomor referensi sinkronisasi berformat `SYNC-GR-{YYYYMMDD}-{UUID}`.
  - `sync_type`: `inbound_po`.
  - `direction`: `outbound`.
  - `payload`: Salinan JSON respon dari SAP (termasuk objek `sap_accounting_log` jika berhasil, atau payload request beserta pesan error jika gagal).
  - `status`: `success` jika respon HTTP 200/201, atau `failed` jika terjadi galat.
- Antarmuka & Aksi Pengiriman Ulang (*Manual Retry*):
  - Formulir `stock.view_picking_form` menampilkan tombol "Send SAP Webhook" / "Retry SAP Webhook" ketika dokumen berstatus `done` dan `sap_sync_status != 'synced'`.
  - Tombol retry dapat dipicu oleh pengguna dalam grup `group_wms_operator` dan `group_wms_manager` untuk mencoba ulang transmisi tanpa mengubah status stok fisik.

#### Scenario: Penyimpanan Respon Simulasi Jurnal Akuntansi SAP pada Audit Log
- **GIVEN** webhook konfirmasi Goods Receipt berhasil diposting ke SAP
- **WHEN** SAP mengembalikan respon status 200 dengan struktur objek `sap_accounting_log` (`journal_entry`, `posting_date`, `debit_account`, `credit_account`, `financial_status`)
- **THEN** sistem membuat baris rekaman baru pada `sap.sync.log` berisi detail payload jurnal akuntansi tersebut untuk transparansi audit

#### Scenario: Pengiriman Ulang Manual Transaksi Webhook yang Sempat Gagal
- **GIVEN** sebuah dokumen penerimaan telah berstatus `done` namun memiliki `sap_sync_status = 'failed'` akibat gangguan jaringan sebelumnya
- **WHEN** operator atau manajer gudang menekan tombol "Retry SAP Webhook" pada formulir picking setelah koneksi pulih
- **THEN** sistem mengeksekusi ulang pengiriman webhook ke SAP, memperbarui `sap_sync_status` menjadi `synced`, dan mencatat transaksi sukses ke `sap.sync.log`

## MODIFIED Requirements
None

## REMOVED Requirements
None

# Specification: Proof of Delivery POD

## Purpose
Menyediakan integrasi otomatis antara pemenuhan bukti serah terima kargo (Proof of Delivery / POD) pada dokumen pengeluaran barang Odoo WMS dengan sistem akuntansi finansial SAP Upper Line melalui transmisi webhook Goods Issue (GI) terotentikasi, fail-safe, dan terefleksi pada log audit.

## ADDED Requirements

### Requirement: [REQ-POD-03] Transmisi Webhook Konfirmasi Goods Issue (GI) dan Respon Akuntansi SAP
The system MUST memicu pengiriman webhook HTTP POST ke endpoint SAP Upper Line / FastAPI (`POST /api/sap/goods-issue`) sesaat setelah dokumen transfer pengeluaran (`stock.picking` dengan `picking_type_code == 'outgoing'`) yang memiliki referensi `sap_doc_number` berstatus `done` dan bukti POD terverifikasi lengkap (`has_pod == True`).
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.3, 3.2, 3.5.3

Spesifikasi protokol, payload, respon, dan penanganan galat:
- **Konfigurasi Host & Kredensial:**
  - Endpoint SAP diambil dari `ir.config_parameter` kunci `wms_sap_connector.sap_base_url` digabungkan dengan rute `/api/sap/goods-issue`.
  - Kredensial otentikasi diambil dari `wms_sap_connector.sap_api_token` dan dikirimkan via header `Authorization: Bearer <token>` serta `X-Odoo-API-Key: <token>`.
- **Payload Request:**
  - `sap_doc_number` (String): Nomor dokumen referensi pesanan pengiriman SAP.
  - `status` (String): `"GOODS_ISSUED"`.
  - `issued_date` (String): Waktu serah terima kargo dalam format ISO 8601 UTC (`%Y-%m-%dT%H:%M:%SZ`).
  - `receiver_name` (String): Nama pihak penerima dari field `pod_signed_by` (atau nilai fallback jika kosong).
  - `has_pod` (Boolean): Bernilai `True` menandakan dokumen serah terima kargo telah valid.
- **Pencatatan Audit Log & Pembaruan Status:**
  - Setiap transmisi webhook menghasilkan kode referensi unik `SYNC-GI-YYYYMMDD-XXXXXX`.
  - Pada respon sukses (HTTP 200/201), sistem mencatat respon JSON lengkap (termasuk blok simulasi jurnal HPP `sap_accounting_log`) ke dalam `sap.sync.log` dengan `sync_type='outbound_so'`, `direction='outbound'`, dan `status='success'`.
  - Field `sap_sync_status` pada `stock.picking` diperbarui menjadi `'synced'`.
- **Eksekusi Non-blocking & Penanganan Kegagalan:**
  - Jika konfigurasi URL kosong, koneksi timeout, atau server SAP mengembalikan status HTTP 4xx/5xx, sistem MUST NOT membatalkan mutasi stok fisik di Odoo (eksekusi bersifat fail-safe dan terisolasi dalam blok try-except).
  - Field `sap_sync_status` pada `stock.picking` diubah menjadi `'failed'`, dan insiden kegagalan dicatat ke dalam `sap.sync.log` dengan `status='failed'` dan `error_message` yang mendeskripsikan rincian galat.
- **Pemicu Susulan dan Tombol Aksi Manual:**
  - Jika transfer divalidasi ke status `done` sebelum bukti POD diunggah, webhook tidak dikirimkan terlebih dahulu. Saat bukti POD (`proof_of_delivery` atau `pod_signed_by`) kemudian diunggah ke dokumen transfer `done` tersebut, sistem secara otomatis memicu transmisi webhook Goods Issue.
  - Pengguna berhak akses dapat memicu atau mengirim ulang webhook sewaktu-waktu melalui tombol aksi `"Send Goods Issue to SAP"` (`action_send_sap_goods_issue_webhook`) pada header formulir Delivery Order.

#### Scenario: Transmisi Otomatis Webhook Goods Issue Saat Validasi Transfer dengan POD Lengkap (Happy Path)
- **GIVEN** dokumen Delivery Order bertipe `outgoing` dengan `sap_doc_number = "SO-DELIV-2026-901"` yang telah dilengkapi berkas foto POD dan penerima (`has_pod == True`)
- **WHEN** staf gudang memvalidasi transfer menjadi berstatus `done` melalui `button_validate()`
- **THEN** sistem menembakkan webhook HTTP POST ke endpoint SAP `/api/sap/goods-issue`, menerima respon sukses simulasi jurnal HPP, memperbarui `sap_sync_status` menjadi `synced`, dan mencatat transaksi ke `sap.sync.log`

#### Scenario: Pengunggahan Bukti POD Susulan pada Transfer Berstatus Done Memicu Webhook Otomatis (Happy Path)
- **GIVEN** dokumen Delivery Order berstatus `done` yang awalnya belum memiliki bukti POD (`has_pod == False`)
- **WHEN** dispatcher atau kurir mengunggah gambar `proof_of_delivery` dan nama penerima `pod_signed_by = "Budi Santoso"` pada formulir transfer
- **THEN** sistem menyimpan dokumen, mengomputasi `has_pod = True`, dan secara otomatis mengeksekusi transmisi webhook Goods Issue ke SAP

#### Scenario: Pengiriman Ulang Manual Webhook Goods Issue Melalui Tombol Aksi Formulir (Happy Path)
- **GIVEN** dokumen Delivery Order berstatus `done` dengan `sap_doc_number` dan status sinkronisasi `failed` akibat kendala jaringan sebelumnya
- **WHEN** pengguna mengklik tombol `"Send Goods Issue to SAP"` pada header formulir transfer
- **THEN** sistem mengeksekusi ulang transmisi webhook ke SAP, memperbarui `sap_sync_status` menjadi `synced` jika sukses, dan menambahkan rekaman audit baru di `sap.sync.log`

#### Scenario: Kegagalan Jaringan Webhook SAP Tidak Membatalkan Validasi Fisik Transfer (Edge Case)
- **GIVEN** dokumen Delivery Order yang telah memiliki bukti POD lengkap, namun endpoint server SAP tidak dapat dihubungi (timeout atau offline)
- **WHEN** staf gudang memvalidasi transfer stok hingga berstatus `done`
- **THEN** mutasi stok fisik barang di Odoo tetap berhasil berstatus `done`, status `sap_sync_status` pada picking ditandai `failed`, dan pesan galat teknis terekam pada `sap.sync.log` tanpa memunculkan exception blocking ke antarmuka pengguna

## MODIFIED Requirements
None

## REMOVED Requirements
None

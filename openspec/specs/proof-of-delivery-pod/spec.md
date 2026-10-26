# Specification: Proof of Delivery POD

## Purpose
Menyediakan kemampuan pencatatan, penangkapan berkas visual bukti penerimaan fisik (tanda tangan digital atau foto serah terima kargo), nama terang pihak penerima, dan timestamp waktu penyerahan secara digital pada dokumen pengeluaran barang (Delivery Order) untuk mendukung transparansi operasional dan audit logistik.

## Requirements

### Requirement: [REQ-POD-01] Atribut dan Penyimpanan Bukti Serah Terima Digital (Proof of Delivery)
The system MUST menyediakan atribut penyimpanan bukti serah terima digital pada dokumen transfer `stock.picking` yang mencakup berkas foto/tanda tangan (`proof_of_delivery`), nama terang penerima kargo (`pod_signed_by`), timestamp serah terima (`pod_timestamp`), serta status terkomputasi ketersediaan POD (`has_pod`).
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Spesifikasi atribut dan perilaku data:
- `proof_of_delivery` (Binary):
  - Label: `"Proof of Delivery (Image / Signature)"`
  - Disimpan sebagai lampiran berkas dokumen (`attachment=True`) untuk mencegah beban ukuran baris tabel database.
  - Tidak disalin saat duplikasi dokumen (`copy=False`).
- `pod_signed_by` (Char):
  - Label: `"Received / Signed By"`
  - Nama terang pihak toko/pelanggan yang menerima kargo di lokasi tujuan.
  - Tidak disalin saat duplikasi dokumen (`copy=False`).
- `pod_timestamp` (Datetime):
  - Label: `"POD Timestamp"`
  - Waktu pencatatan bukti penyerahan barang di sistem.
  - Jika pengguna mengunggah `proof_of_delivery` atau mengisi `pod_signed_by` tanpa menentukan `pod_timestamp`, sistem secara otomatis mengisi `pod_timestamp` dengan waktu saat ini (`fields.Datetime.now()`).
  - Tidak disalin saat duplikasi dokumen (`copy=False`).
- `has_pod` (Boolean, Read-only):
  - Label: `"Has POD"`
  - Bernilai `True` jika `proof_of_delivery` telah terisi atau `pod_signed_by` telah dicatat; sebaliknya bernilai `False`.
  - Terkomputasi dari `@api.depends('proof_of_delivery', 'pod_signed_by')` dan tersimpan di basis data (`store=True`, `index=True`).

#### Scenario: Pencatatan Bukti Serah Terima Kargo Lengkap oleh Supir atau Dispatcher (Happy Path)
- **GIVEN** dokumen Delivery Order (`stock.picking` bertipe `outgoing`) yang telah berstatus `assigned` atau `done`
- **WHEN** staf gudang atau supir mengunggah foto serah terima pada `proof_of_delivery` dan memasukkan nama penerima `Budi Santoso (Alfamart)`
- **THEN** sistem menyimpan dokumen, mengisi `pod_timestamp` secara otomatis jika belum diisi manual, dan memperbarui `has_pod` menjadi `True`

#### Scenario: Otomatisasi Timestamp POD Saat Bukti Diunggah Tanpa Menentukan Waktu (Happy Path)
- **GIVEN** dokumen transfer pengeluaran barang tanpa data POD sebelumnya
- **WHEN** pengguna mengunggah berkas `proof_of_delivery` dengan mengosongkan field `pod_timestamp`
- **THEN** sistem menetapkan nilai `pod_timestamp` secara otomatis dengan timestamp waktu saat ini dan menyimpan record

### Requirement: [REQ-POD-02] Antarmuka Pencatatan dan Filter Bukti Serah Terima pada Transfer Pengeluaran Barang
The system MUST menyajikan antarmuka visual khusus untuk pengunggahan bukti serah terima (POD), pratinjau gambar, serta filter pencarian dokumen berdasarkan kelengkapan status POD pada modul inventori Odoo 17.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.3, 3.2

Spesifikasi antarmuka pengguna:
- Form View (`stock.view_picking_form`):
  - Ditambahkan halaman notebook tersendiri `page_proof_of_delivery` berlabel `"Proof of Delivery (POD)"`.
  - Hanya ditampilkan secara dinamis pada transfer kargo pengeluaran (`invisible="picking_type_code != 'outgoing'"`).
  - Memuat field `proof_of_delivery` dengan widget gambar (`widget="image"` atau visual signature preview) serta grup rincian legalitas (`pod_signed_by`, `pod_timestamp`, `has_pod`).
- Tree View (`vpicktree_inherit_sap`):
  - Ditambahkan kolom `pod_signed_by` dan `pod_timestamp` dalam opsi tampilan opsional (`optional="hide"`).
- Search View (`stock.view_picking_internal_search`):
  - Filter cepat `"Has POD"` (`domain="[('has_pod', '=', True)]"`).
  - Filter cepat `"Missing POD"` (`domain="[('picking_type_code', '=', 'outgoing'), ('has_pod', '=', False)]"`).

#### Scenario: Pratinjau Bukti Gambar dan Data Penerima pada Formulir Pengantaran (Happy Path)
- **GIVEN** dokumen Delivery Order yang telah memiliki berkas bukti serah terima
- **WHEN** staf gudang atau manajer membuka formulir transfer pada tab "Proof of Delivery (POD)"
- **THEN** sistem menampilkan pratinjau visual gambar bukti penyerahan beserta nama terang penerima dan timestamp serah terima

#### Scenario: Penyaringan Dokumen Pengantaran yang Belum Memiliki Bukti POD (Happy Path)
- **GIVEN** daftar dokumen pengeluaran barang di mana sebagian transfer telah memiliki POD dan sebagian belum
- **WHEN** dispatcher menerapkan filter "Missing POD" pada kotak pencarian transfer
- **THEN** sistem hanya menampilkan dokumen transfer pengeluaran barang yang belum memiliki rekaman bukti POD (`has_pod == False`)

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

# Specification: Proof of Delivery POD

## Purpose
Menyediakan kemampuan pencatatan, penangkapan berkas visual bukti penerimaan fisik (tanda tangan digital atau foto serah terima kargo), nama terang pihak penerima, dan timestamp waktu penyerahan secara digital pada dokumen pengeluaran barang (Delivery Order) untuk mendukung transparansi operasional dan audit logistik.

## ADDED Requirements

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

## MODIFIED Requirements
None

## REMOVED Requirements
None

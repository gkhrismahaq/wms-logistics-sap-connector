# Specification: Outbound Dispatch Surat Jalan

## ADDED Requirements

### Requirement: [REQ-OUT-06] Penerbitan dan Pencetakan Dokumen Resmi Surat Jalan Pengantaran Barang (Official Delivery Slip)
The system MUST menyediakan laporan resmi cetak dokumen Surat Jalan (*Official Delivery Slip*) berformat QWeb PDF untuk setiap dokumen pengeluaran barang (`stock.picking` bertipe `outgoing`), yang memuat kop identitas DC, barcode dokumen standar Code128, metadata tujuan, rincian kargo, atribut armada dan supir, serta kolom pengesahan legalitas tiga pihak.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 1.3

Spesifikasi tata letak dan struktur dokumen Surat Jalan:
- Tindakan Laporan (`ir.actions.report`):
  - Model target: `stock.picking`.
  - Tipe laporan: `qweb-pdf`.
  - ID dan Nama Laporan: `wms_sap_connector.report_surat_jalan`.
  - Binding Model: `stock.picking` (tersedia di menu Print / Action).
  - Tombol Akses Cepat: Tersedia tombol "Print Surat Jalan" pada header form view transfer pengeluaran barang (`picking_type_code == 'outgoing'`).
- Elemen Konten Dokumen:
  - Header & Kop Dokumen:
    - Logo perusahaan dan nama fasilitas logistik ("DC Lowokwaru / Madura Mart").
    - Judul Dokumen: "SURAT JALAN PENGANTARAN BARANG (DELIVERY SLIP)".
    - Nomor Dokumen Transfer (`o.name`) dan Barcode Code128 (`/report/barcode/?barcode_type=Code128&value=...`).
    - Nomor Referensi SAP Upper Line (`o.sap_doc_number`) jika tersedia.
    - Tanggal Cetak Dokumen dan Tanggal Jadwal Pengantaran (`o.scheduled_date`).
  - Informasi Tujuan & Pelanggan:
    - Nama Pelanggan / Toko Penerima (`o.partner_id.name`).
    - Alamat Lengkap Pengiriman (`o.partner_id.street`, `o.partner_id.city`, dsb).
    - Kontak Penerima jika tersedia.
  - Informasi Armada & Muatan Kargo:
    - Nomor Polisi Kendaraan (`o.vehicle_id.license_plate`).
    - Nama Supir Pengantar (`o.driver_id.name`).
    - Akumulasi Total Berat Muatan (`o.total_weight` kg).
    - Akumulasi Total Volume Muatan (`o.total_volume` m³).
  - Tabel Rincian Barang Kargo:
    - Kolom Nomor Urut.
    - Kode Material SAP / SKU (`move.product_id.sap_material_code` atau `move.product_id.default_code`).
    - Deskripsi Nama Barang (`move.product_id.name`).
    - Kuantitas yang Dikirim (`move.product_uom_qty` atau `move.quantity`).
    - Satuan Pengukuran (`move.product_uom.name`).
  - Area Pengesahan & Tanda Tangan Fisik (3 Kolom):
    - Kolom 1: Disiapkan / Dikeluarkan Oleh (*Prepared By / Dispatcher*).
    - Kolom 2: Dibawa / Diantar Oleh (*Delivered By / Driver*).
    - Kolom 3: Diterima Oleh (*Received By / Store Receiver*).

#### Scenario: Pencetakan Dokumen Surat Jalan Berhasil dengan Kelengkapan Data Armada dan Barcode (Happy Path)
- **GIVEN** dokumen Delivery Order (`stock.picking` bertipe `outgoing`) yang telah dialokasikan dengan armada kendaraan `B 1234 WMS`, supir `Budi Santoso`, serta memiliki baris pergerakan stok kargo
- **WHEN** staf gudang atau dispatcher menekan tombol "Print Surat Jalan" atau memicu action report `wms_sap_connector.report_surat_jalan`
- **THEN** sistem menghasilkan berkas QWeb PDF Surat Jalan yang memuat kop DC Lowokwaru, barcode Code128 nomor dokumen, rincian nomor polisi dan supir, total berat dan volume muatan, tabel baris kargo, serta 3 kolom tanda tangan pengesahan

#### Scenario: Pencetakan Dokumen Surat Jalan Sebelum Penugasan Armada (Edge Case)
- **GIVEN** dokumen Delivery Order yang telah terkonfirmasi namun armada (`vehicle_id`) dan supir (`driver_id`) belum ditugaskan
- **WHEN** pengguna mencetak dokumen Surat Jalan
- **THEN** sistem tetap berhasil menghasilkan berkas QWeb PDF tanpa memicu error, dengan menampilkan penanda kosong atau tanda hubung ("-") pada informasi armada dan supir pengantar

## MODIFIED Requirements
None

## REMOVED Requirements
None

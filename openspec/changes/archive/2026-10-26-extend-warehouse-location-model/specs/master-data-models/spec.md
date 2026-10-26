# Specification: Master Data Models

## Purpose
Menyediakan perluasan model data inti Odoo (termasuk Material/Produk, Mitra Bisnis, dan Lokasi Gudang) dengan atribut identifikasi unik SAP serta spesifikasi fisik kargo guna menjamin sinkronisasi master data yang presisi dan mendukung eksekusi logistik pergudangan.

## ADDED Requirements

### Requirement: [REQ-MD-03] Perluasan Model Data Lokasi Gudang untuk Integrasi SAP dan Identifikasi Rak Fisik
The system MUST memperluas model `stock.location` dengan menambahkan bidang data `sap_plant_code` (Char, `index=True`), `sap_sloc_code` (Char, `index=True`), dan memastikan `barcode` (Char, `index=True`, `copy=False`) sebagai pengenal barcode fisik rak gudang, serta menyajikannya pada formulir lokasi Odoo.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Spesifikasi teknis atribut model `stock.location`:
- `sap_plant_code` (Char, Index): Menyimpan kode Plant / Pabrik pada sistem SAP (contoh: `1000`) yang menaungi gudang bersangkutan.
- `sap_sloc_code` (Char, Index): Menyimpan kode Storage Location pada sistem SAP (contoh: `SL01`, `1001`).
- `barcode` (Char, Index, Copy=False): Menyimpan nilai barcode fisik yang ditempel pada lorong atau rak penyimpanan untuk pemindaian scanner barcode staf gudang saat proses alokasi (*putaway*) atau pengambilan (*picking*).
- Perilaku duplikasi: Bidang `barcode` MUST NOT disalin saat pengguna melakukan tindakan duplikasi record lokasi (`copy=False`).
- Indeks database: Kolom `sap_plant_code`, `sap_sloc_code`, dan `barcode` MUST diindeks menggunakan indeks B-Tree pada basis data PostgreSQL untuk menjamin kecepatan kueri pencarian saat alur barang masuk dan validasi rak.

#### Scenario: Penambahan dan Penyimpanan Kode SAP dan Barcode pada Lokasi Gudang
- **GIVEN** pengguna dengan hak akses manajerial gudang membuka formulir pembuatan atau pengubahan lokasi gudang (`stock.location`)
- **WHEN** pengguna mengisikan nilai kode Plant SAP, kode SLoc SAP, serta kode barcode rak fisik lalu menekan tombol simpan
- **THEN** sistem berhasil menyimpan data lokasi ke basis data lengkap dengan indeks aktif dan menyajikannya pada formulir lokasi

#### Scenario: Duplikasi Record Lokasi Tanpa Menyalin Nilai Barcode Rak
- **GIVEN** sebuah lokasi gudang telah terdaftar dengan nilai `barcode` rak fisik tertentu
- **WHEN** pengguna melakukan tindakan duplikasi (*duplicate*) terhadap record lokasi tersebut
- **THEN** sistem membuat salinan lokasi baru dengan field `barcode` bernilai kosong (`False`) untuk mencegah duplikasi kode barcode rak pada lokasi fisik yang berbeda

#### Scenario: Pencarian Lokasi Gudang Berdasarkan Kode Plant dan SLoc SAP
- **GIVEN** master data lokasi gudang di Odoo telah dipetakan dengan `sap_plant_code` dan `sap_sloc_code` tertentu
- **WHEN** layanan integrasi atau modul penerimaan inbound mencari lokasi penyimpanan berdasarkan kode SAP Plant dan SLoc
- **THEN** sistem secara akurat mengembalikan record `stock.location` yang bersangkutan dengan memanfaatkan indeks basis data

## MODIFIED Requirements
None

## REMOVED Requirements
None

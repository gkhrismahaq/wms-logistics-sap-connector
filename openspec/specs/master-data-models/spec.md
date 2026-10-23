# Specification: Master Data Models

## Purpose
Menyediakan perluasan model data inti Odoo (termasuk Material/Produk, Mitra Bisnis, dan Lokasi Gudang) dengan atribut identifikasi unik SAP serta spesifikasi fisik kargo guna menjamin sinkronisasi master data yang presisi dan mendukung eksekusi logistik pergudangan.

## Requirements

### Requirement: [REQ-MD-01] Perluasan Model Data Material Produk untuk Integrasi SAP dan Verifikasi Gudang
The system MUST memperluas model `product.template` dengan menambahkan bidang data `sap_material_code` (Char, `index=True`, `copy=False`) sebagai pengenal unik SKU sistem SAP, serta memastikan atribut fisik kargo (`weight`, `volume`) dan widget foto produk (`image_1920`) dapat diakses dan disajikan pada formulir produk Odoo.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Spesifikasi teknis atribut model `product.template`:
- `sap_material_code` (Char, Index, Copy=False): Menyimpan kode unik SKU/material dari sistem SAP (contoh: `MAT-KOPI-01`).
- `weight` (Float): Berat netto per unit produk (kg) untuk kalkulasi beban armada kargo logistik.
- `volume` (Float): Dimensi volume kubikasi produk (m³) untuk perencanaan muatan kargo.
- `image_1920` (Binary): Foto produk resolusi tinggi untuk verifikasi visual staf picker/packer di gudang dan menerima data gambar (Base64) dari SAP.
- Perilaku duplikasi: Bidang `sap_material_code` MUST NOT disalin saat pengguna melakukan aksi duplikasi record produk (`copy=False`).

#### Scenario: Penambahan dan Penyimpanan Kode Material SAP pada Produk
- **GIVEN** pengguna dengan hak akses manajerial gudang membuka formulir pembuatan atau pengubahan produk
- **WHEN** pengguna mengisikan nilai kode material SAP pada field `sap_material_code` lalu menekan tombol simpan
- **THEN** sistem berhasil menyimpan nilai tersebut ke basis data dengan indeks pencarian aktif dan menyajikannya pada formulir produk

#### Scenario: Duplikasi Record Produk Tanpa Menyalin Kode Material SAP
- **GIVEN** sebuah produk telah memiliki kode material SAP `sap_material_code` yang terdaftar
- **WHEN** pengguna melakukan tindakan duplikasi (*duplicate*) terhadap record produk tersebut
- **THEN** sistem membuat salinan record produk baru dengan field `sap_material_code` bernilai kosong (`False`) guna mencegah duplikasi kode referensi SAP

#### Scenario: Verifikasi Visual dan Spesifikasi Fisik Produk oleh Staf Gudang
- **GIVEN** sebuah produk memiliki data gambar `image_1920` serta spesifikasi berat dan volume
- **WHEN** staf gudang (picker/packer) membuka formulir produk untuk pemeriksaan barang
- **THEN** sistem menyajikan foto produk secara visual bersama rincian berat dan volume untuk verifikasi fisik kargo tanpa memperkenankan modifikasi data jika pengguna tidak memiliki wewenang manajerial

### Requirement: [REQ-MD-02] Perluasan Model Data Mitra Rekanan Bisnis untuk Integrasi SAP
The system MUST memperluas model `res.partner` dengan menambahkan bidang data `sap_partner_code` (Char, `index=True`, `copy=False`) sebagai pengenal unik entitas Vendor dan Customer pada sistem SAP, serta menyajikannya pada formulir kontak Odoo.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Spesifikasi teknis atribut model `res.partner`:
- `sap_partner_code` (Char, Index, Copy=False): Menyimpan kode unik Vendor atau Customer dari sistem SAP (contoh: `VEND-INDOMARCO`, `CUST-ALFAMART-01`).
- Perilaku duplikasi: Bidang `sap_partner_code` MUST NOT disalin saat pengguna melakukan aksi duplikasi record kontak (`copy=False`).
- Indeks database: Kolom `sap_partner_code` MUST diindeks menggunakan indeks B-Tree pada basis data PostgreSQL untuk mendukung efisiensi query pencarian dan rekonsiliasi integrasi.

#### Scenario: Penambahan dan Penyimpanan Kode Rekanan SAP pada Kontak
- **GIVEN** pengguna dengan hak administratif membuka formulir pembuatan atau pengubahan rekanan (`res.partner`)
- **WHEN** pengguna mengisikan nilai kode identifikasi SAP pada field `sap_partner_code` lalu menekan tombol simpan
- **THEN** sistem berhasil menyimpan nilai tersebut ke basis data dengan indeks aktif dan menyajikannya pada formulir kontak

#### Scenario: Duplikasi Record Kontak Tanpa Menyalin Kode Rekanan SAP
- **GIVEN** sebuah record mitra telah memiliki nilai `sap_partner_code` yang tersimpan
- **WHEN** pengguna melakukan aksi duplikasi (*duplicate*) terhadap record rekanan tersebut
- **THEN** sistem membuat salinan kontak baru dengan nilai field `sap_partner_code` kosong (`False`) untuk mencegah tumpang tindih kode referensi unik SAP

#### Scenario: Pencarian Rekanan Berdasarkan Kode SAP untuk Integrasi Transaksi
- **GIVEN** data rekanan telah tersimpan di Odoo dengan nilai `sap_partner_code` tertentu
- **WHEN** modul integrasi melakukan pencarian data rekanan berdasarkan kriteria `sap_partner_code`
- **THEN** sistem secara akurat mengembalikan record `res.partner` yang sesuai dengan memanfaatkan indeks basis data

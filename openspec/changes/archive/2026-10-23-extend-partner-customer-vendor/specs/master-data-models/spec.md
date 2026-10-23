# Specification: Master Data Models

## Purpose
Menyediakan perluasan model data inti Odoo (termasuk Material/Produk, Mitra Bisnis, dan Lokasi Gudang) dengan atribut identifikasi unik SAP serta spesifikasi fisik kargo guna menjamin sinkronisasi master data yang presisi dan mendukung eksekusi logistik pergudangan.

## ADDED Requirements

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

## MODIFIED Requirements
None

## REMOVED Requirements
None

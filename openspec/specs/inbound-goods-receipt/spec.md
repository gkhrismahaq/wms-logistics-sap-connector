# Specification: Inbound Goods Receipt

## Purpose
Menyediakan kemampuan penautan, pelacakan referensi dokumen pesanan pembelian (*Purchase Order*) SAP, dan monitoring status siklus hidup sinkronisasi pada dokumen penerimaan barang (*Stock Picking Inbound*) WMS Odoo 17.

## Requirements

### Requirement: [REQ-INB-01] Perluasan Model Dokumen Picking untuk Referensi Dokumen SAP dan Status Sinkronisasi
The system MUST memperluas model ORM `stock.picking` dengan menambahkan bidang data `sap_doc_number` dan `sap_sync_status` guna menyimpan referensi dokumen asal dari SAP serta memonitor status siklus integrasi data.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Spesifikasi teknis atribut model `stock.picking`:
- `sap_doc_number`: Tipe `fields.Char`, terindeks B-Tree (`index=True`), tidak disalin saat duplikasi record (`copy=False`), menyimpan nomor identitas pesanan pembelian dari SAP (contoh: `PO-SAP-2026-001`).
- `sap_sync_status`: Tipe `fields.Selection`, nilai opsi:
  - `draft`: 'Draft / Belum Disinkronkan'
  - `pending`: 'Menunggu Sinkronisasi'
  - `synced`: 'Tersinkronisasi ke SAP'
  - `failed`: 'Gagal Sinkronisasi'
  - Nilai default disetel ke `draft`, terindeks (`index=True`), dan tidak disalin saat duplikasi record (`copy=False`).

#### Scenario: Pembuatan Dokumen Picking Baru dengan Referensi Dokumen SAP
- **GIVEN** staf gudang atau layanan otomatis membuat dokumen penerimaan barang (`stock.picking` tipe `incoming`)
- **WHEN** nomor dokumen SAP `PO-SAP-2026-001` disematkan pada pembuatan record
- **THEN** sistem berhasil menyimpan record dengan field `sap_doc_number = 'PO-SAP-2026-001'` dan `sap_sync_status = 'draft'`

#### Scenario: Perubahan Status Sinkronisasi Dokumen Inbound
- **GIVEN** sebuah dokumen picking inbound telah divalidasi dan siap dikonfirmasi ke SAP
- **WHEN** proses sinkronisasi mengubah status siklus hidup
- **THEN** sistem memperbarui field `sap_sync_status` menjadi `pending`, `synced`, atau `failed` sesuai hasil proses tanpa merusak data transfer stok

### Requirement: [REQ-INB-02] Visibilitas dan Antarmuka Pengguna Dokumen Inbound SAP
The system MUST menyajikan field `sap_doc_number` dan `sap_sync_status` pada antarmuka formulir dokumen penerimaan (`stock.view_picking_form`), tampilan daftar / list view (`stock.vpicktree`), serta menyediakan filter dan pengelompokan pada antarmuka pencarian (`stock.view_picking_internal_search`).
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Spesifikasi teknis antarmuka:
- Formulir (`stock.view_picking_form`): Field `sap_doc_number` dan `sap_sync_status` ditampilkan pada header atau area informasi utama dokumen picking.
- Tampilan Daftar (`stock.vpicktree`): Kolom `sap_doc_number` dan `sap_sync_status` ditampilkan dengan widget badge berdekorasi warna (`decoration-success="sap_sync_status == 'synced'"`, `decoration-danger="sap_sync_status == 'failed'"`, `decoration-warning="sap_sync_status == 'pending'"`).
- Pencarian (`stock.view_picking_internal_search`): Menyediakan filter pencarian instan berdasarkan nomor dokumen SAP serta opsi *Group By* berdasarkan `sap_sync_status`.

#### Scenario: Penelusuran Dokumen Picking Berdasarkan Nomor Dokumen SAP pada Search View
- **GIVEN** terdapat sejumlah dokumen penerimaan barang di dalam database
- **WHEN** staf gudang mengetikkan nomor dokumen SAP `PO-SAP-2026-001` pada bilah pencarian
- **THEN** sistem menampilkan dokumen picking yang memiliki kecocokan tepat pada field `sap_doc_number`

#### Scenario: Pengelompokan Dokumen Berdasarkan Status Sinkronisasi
- **GIVEN** daftar penerimaan barang dibuka pada modul persediaan
- **WHEN** pengguna memilih opsi Group By `SAP Sync Status`
- **THEN** sistem mengelompokkan dokumen berdasarkan status sinkronisasi (`draft`, `pending`, `synced`, `failed`)

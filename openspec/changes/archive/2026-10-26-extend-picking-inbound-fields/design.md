# Design Document: Extend Picking Inbound Fields

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | extend-picking-inbound-fields                 |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `stock.picking`                               |

## Context
Pada arsitektur Two-Tier WMS & SAP Connector, dokumen penerimaan fisik barang pesanan pembelian (*Purchase Order*) di Odoo direpresentasikan oleh entitas `stock.picking` dengan tipe operasi penerimaan (`picking_type_id.code == 'incoming'`). Agar dokumen ini dapat mencerminkan nomor referensi resmi dokumen SAP serta memantau status siklus hidup pertukaran data (sinkronisasi), model bawaan Odoo perlu diperluas secara non-destruktif.

Perluasan ini menjadi pondasi data sebelum dibangunnya Odoo REST Controller penerima PO (`/api/sap/inbound/po`) pada change berikutnya dalam Fase 3.

## Goals / Non-Goals
### Goals
- Mewarisi (*inherit*) model `stock.picking` dengan menambahkan field `sap_doc_number` dan `sap_sync_status`.
- Menambahkan indeks B-Tree pada field `sap_doc_number` dan `sap_sync_status` untuk performa tinggi saat pencarian dan filter API.
- Mengonfigurasi `copy=False` pada kedua field agar tidak terduplikasi saat record disalin manual di UI.
- Memperluas formulir penerimaan barang (`stock.view_picking_form`) untuk menampilkan nomor referensi SAP dan status sinkronisasi.
- Memperluas tampilan daftar (`stock.vpicktree`) dengan kolom status berdekorasi warna (*badge*).
- Memperluas filter pencarian (`stock.view_picking_internal_search`) dengan pencarian instan nomor dokumen SAP dan pengelompokan (*group by*) status sinkronisasi.

### Non-Goals
- Tidak mengimplementasikan endpoint REST API `/api/sap/inbound/po` pada change ini (lingkup change `api-receive-sap-purchase-order`).
- Tidak mengimplementasikan transmisi webhook konfirmasi Goods Receipt ke SAP pada change ini (lingkup change `webhook-notify-sap-goods-receipt`).
- Tidak menambahkan field logistik armada atau bukti serah terima POD pada change ini (lingkup Fase 4 Outbound).

## Decisions (ADR)
### 1. Pewarisan Model Inti stock.picking Menggunakan `_inherit`
- **Rationale:** Memanfaatkan mekanisme inheritance ORM Odoo 17 untuk menambahkan field ke model `stock.picking` tanpa mengubah kode inti (*core*) Odoo. Hal ini memastikan operasional gudang tetap dapat menikmati fitur bawaan Odoo seperti barcode scanner, reservasi stok, dan putaway rules.
- **Alternatives Considered:** Membuat model kustom terpisah `sap.purchase.order.inbound`. Opsi ini ditolak karena memecah alur penerimaan barang Odoo dan membutuhkan relasi manual tambahan yang memperumit antarmuka staf gudang.
- **Consequences:** Seluruh tipe picking di modul persediaan memiliki akses ke field ini, dengan penempatan yang disesuaikan secara rapi pada antarmuka.

### 2. Pengindeksan B-Tree dan Kebijakan `copy=False`
- **Rationale:** Pada arsitektur integrasi, pencarian record berdasarkan `sap_doc_number` terjadi secara intensif saat panggilan API inbound dan rekonsiliasi data. Menambahkan `index=True` memastikan pencarian berskala $O(\log n)$. Atribut `copy=False` mutlak dipasang agar nomor dokumen referensi SAP tidak terbawa jika staf gudang melakukan duplikasi dokumen.
- **Alternatives Considered:** Tidak mengindeks field `sap_doc_number`. Opsi ini ditolak karena pemindaian sekuensial (*full table scan*) akan menurunkan performa ketika volume transaksi mencapai puluhan ribu record.
- **Consequences:** Membutuhkan alokasi indeks kecil di PostgreSQL namun memberikan jaminan query yang sangat responsif.

### 3. Struktur Nilai Enum `sap_sync_status`
- **Rationale:** Siklus integrasi dokumen inbound membutuhkan tahapan status yang jelas: `draft` (baru dibuat/belum disinkronkan), `pending` (menunggu pemrosesan antrian/webhook), `synced` (berhasil dikonfirmasi dan sinkron dengan SAP), dan `failed` (terjadi kendala jaringan/validasi).
- **Alternatives Considered:** Menggunakan field boolean sederhana `is_synced`. Opsi ini ditolak karena tidak dapat membedakan kondisi dokumen yang sedang dalam proses pengiriman antrian (*pending*) atau yang mengalami galat teknis (*failed*).
- **Consequences:** Memungkinkan visualisasi badge status warna-warni pada tampilan pohon (*tree view*) yang memudahkan pengawasan oleh Kepala Gudang.

## Technical Architecture & Data Schema

### 1. Deklarasi Model Python (`addons/wms_sap_connector/models/stock_picking.py`)
```python
# -*- coding: utf-8 -*-
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    sap_doc_number = fields.Char(
        string="SAP Document Number",
        index=True,
        copy=False,
        help="Nomor referensi dokumen pesanan pembelian atau pengiriman asal di SAP (misal: PO-SAP-2026-001).",
    )
    sap_sync_status = fields.Selection(
        [
            ("draft", "Draft / Not Synced"),
            ("pending", "Pending Sync"),
            ("synced", "Synced to SAP"),
            ("failed", "Sync Failed"),
        ],
        string="SAP Sync Status",
        default="draft",
        index=True,
        copy=False,
        help="Status siklus hidup sinkronisasi dokumen transaksi dengan SAP.",
    )
```

### 2. Struktur XML Views (`addons/wms_sap_connector/views/stock_picking_views.xml`)
- **Form View Extension (`stock.view_picking_form`):**
  Menggunakan anchor XPath `//field[@name='origin']` untuk meletakkan field `sap_doc_number` dan `sap_sync_status`.
- **Tree View Extension (`stock.vpicktree`):**
  Menggunakan anchor XPath `//field[@name='origin']` untuk menyematkan kolom `sap_doc_number` dan badge status dekoratif `sap_sync_status`.
- **Search View Extension (`stock.view_picking_internal_search`):**
  Menambahkan field pencarian `sap_doc_number` dan filter pengelompokan Group By `sap_sync_status`.

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Benturan XPath pada form view saat ada modul pihak ketiga | Low | Menggunakan anchor posisi yang stabil dan universal (`//field[@name='origin']` position="after"). |
| Duplikasi nomor dokumen SAP saat request berulang | Medium | Pada level database dipasang indeks, dan pada level endpoint controller berikutnya diterapkan pencarian idempoten sebelum create/write. |
| Nilai status default mengaburkan dokumen non-SAP | Low | Nilai default `draft` adalah standar aman; dokumen reguler yang dibuat manual tetap berstatus draft tanpa mengganggu operasional normal. |

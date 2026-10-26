# Proposal: Extend Picking Inbound Fields

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | extend-picking-inbound-fields                 |
| **Roadmap Phase**  | Fase 3: Alur Barang Masuk & Penempatan Rak (Inbound & Putaway) |
| **Target Cap.**    | `inbound-goods-receipt`                       |
| **Est. Effort**    | 3 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Dalam arsitektur Two-Tier ERP antara SAP dan Odoo WMS, proses penerimaan barang fisik di gudang (*Inbound Goods Receipt*) berakar dari pesanan pembelian (*Purchase Order*) yang diterbitkan di sistem SAP Upper Line. Agar dokumen penerimaan barang di Odoo (`stock.picking` bertipe operasi `incoming`) dapat ditautkan secara langsung dan akurat dengan dokumen asal di SAP tanpa kebingungan nomor referensi, model `stock.picking` wajib diperluas dengan field `sap_doc_number` (sebagai nomor referensi PO SAP) dan field `sap_sync_status` (untuk memonitor siklus hidup sinkronisasi dokumen: draft, pending, synced, atau failed). Tanpa kedua atribut ini, staf gudang dan layanan integrasi tidak memiliki landasan data untuk melacak referensi pesanan SAP, memicu konfirmasi penerimaan barang, maupun memfilter dokumen inbound secara terintegrasi pada antarmuka Odoo.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 3 (Kapabilitas 3.1).

## What Changes
Perubahan mencakup penambahan model ekstensi untuk `stock.picking`, pendaftaran field referensi SAP, serta penyesuaian antarmuka form, tree, dan filter pencarian:
- **Backend (ORM & Models):** Mewarisi (*inherit*) model inti Odoo `stock.picking` pada file baru `addons/wms_sap_connector/models/stock_picking.py` dengan menambahkan field `sap_doc_number` (`fields.Char`, index=True, copy=False) dan `sap_sync_status` (`fields.Selection`, default='draft', index=True, copy=False).
- **Security & Access Rights:** Model bawaan `stock.picking` telah memiliki aturan hak akses standar Odoo. Field baru dapat diakses dan dilihat oleh grup pengguna WMS (`group_wms_operator`, `group_wms_dispatcher`, `group_wms_manager`).
- **Views & UI:** Membuat file view baru `addons/wms_sap_connector/views/stock_picking_views.xml` yang meng-inherit form view (`stock.view_picking_form`), tree/list view (`stock.vpicktree`), dan search view (`stock.view_picking_internal_search`) untuk menampilkan kolom `sap_doc_number` dan badge `sap_sync_status`, serta filter pencarian dokumen SAP.
- **Integration & API:** Menyediakan dasar struktur model untuk integrasi inbound PO pada change berikutnya (`api-receive-sap-purchase-order`) dan webhook konfirmasi penerimaan barang (`webhook-notify-sap-goods-receipt`).

## Capabilities
### New Capabilities
- `inbound-goods-receipt`: Otomatisasi pembuatan, penautan referensi dokumen SAP, dan pemrosesan dokumen penerimaan barang pesanan pembelian (*Purchase Order*) pada WMS Odoo 17.

### Modified Capabilities
- `None`

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/models/stock_picking.py`
  - `addons/wms_sap_connector/views/stock_picking_views.xml`
- **Files to Modify:**
  - `addons/wms_sap_connector/models/__init__.py`
  - `addons/wms_sap_connector/__manifest__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 3.2)
  - `docs/roadmap.md` (Fase 3, Kapabilitas 3.1)
- **Estimated Effort:** 3 jam.
- **Complexity & Risk Analysis:** Tingkat risiko rendah (Low). Perubahan hanya melakukan ekstensi non-destruktif pada `stock.picking` menggunakan mekanisme inheritance standar Odoo 17 tanpa mengubah logika transfer bawaan Odoo.

# Proposal: Automate Putaway Bin Allocation

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | automate-putaway-bin-allocation               |
| **Roadmap Phase**  | Fase 3: Alur Barang Masuk & Penempatan Rak (Inbound & Putaway) |
| **Target Cap.**    | `inbound-goods-receipt`                       |
| **Est. Effort**    | 3 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Dalam operasional pergudangan modern (Two-Tier WMS), saat barang dari pesanan pembelian (*Purchase Order*) tiba di area bongkar muat (*docking*), barang tidak boleh diletakkan sembarangan atau dibiarkan hanya tercatat pada lokasi penampungan umum (*general stock*). Untuk memandu staf operasional gudang (*picker/packer*) menempatkan barang pada rak dan lorong (*bin/rack*) fisik yang optimal secara cepat dan presisi, sistem WMS Odoo memerlukan penerapan alur aturan penempatan otomatis (*Putaway Rule*). Dengan aturan penempatan otomatis ini, saat dokumen penerimaan (*Stock Receipt*) diterbitkan dan dikonfirmasi, sistem secara otomatis mengalokasikan destinasi rak simpan fisik (`stock.move.line.location_dest_id`) berdasarkan SKU produk atau kategori material yang sesuai dengan tata letak gudang.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 3 (Kapabilitas 3.1).

## What Changes
Perubahan mencakup konfigurasi aturan penempatan rak otomatis, integrasi alokasi rak pada alur pembuatan dokumen penerimaan barang masuk, serta pemastian hak akses dan keterlihatan data rak bagi operator gudang:
- **Backend (ORM & Models):** Memastikan eksekusi resolusi aturan penempatan otomatis (`stock.location._get_putaway_strategy`) terintegrasi pada model `stock.picking` (metode `create_inbound_from_sap`) saat pembentukan baris perpindahan fisik (`stock.move.line`), sehingga setiap item barang langsung diarahkan ke lokasi rak spesifik (*Shelf/Bin*). Menyediakan data konfigurasi awal (*data seed*) aturan putaway (`stock.putaway.rule`) untuk material master SAP ke rak gudang yang sesuai.
- **Security & Access Rights:** Memastikan hak akses model `stock.putaway.rule` terdaftar secara eksplisit pada `security/ir.model.access.csv` untuk grup `group_wms_operator` (baca) dan `group_wms_manager` (kelola penuh).
- **Views & UI:** Memastikan visibilitas kolom lokasi tujuan rak fisik (*Destination Location / Bin*) pada tab *Operations* dan *Detailed Operations* formulir penerimaan barang (`stock.view_picking_form`) dapat dibaca dengan jelas oleh staf gudang.
- **Integration & API:** Memastikan endpoint REST API `/api/sap/inbound/po` saat menerbitkan dokumen picking otomatis menghasilkan alokasi rak spesifik pada baris `stock.move.line` yang siap dieksekusi fisik.

## Capabilities
### New Capabilities
- `None`

### Modified Capabilities
- `inbound-goods-receipt`: Menambahkan aturan penempatan otomatis (*Putaway Rule*) ke rak fisik pada saat dokumen penerimaan diterbitkan atau dikonfirmasi.

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/data/stock_putaway_data.xml`
- **Files to Modify:**
  - `addons/wms_sap_connector/__manifest__.py`
  - `addons/wms_sap_connector/models/stock_picking.py`
  - `addons/wms_sap_connector/security/ir.model.access.csv`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 2.2.2)
  - `docs/roadmap.md` (Fase 3, Kapabilitas 3.1)
- **Estimated Effort:** 3 jam.
- **Complexity & Risk Analysis:** Rendah (Low). Menggunakan mekanisme standar Odoo 17 `stock.putaway.rule` yang handal dan stabil. Risiko kegagalan alokasi dimitigasi dengan mekanisme *fallback* bertingkat ke lokasi stok induk gudang jika material belum memiliki aturan putaway spesifik.

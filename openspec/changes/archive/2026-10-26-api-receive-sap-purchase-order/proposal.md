# Proposal: API Receive SAP Purchase Order

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | api-receive-sap-purchase-order                |
| **Roadmap Phase**  | Fase 3: Alur Barang Masuk & Penempatan Rak (Inbound & Putaway) |
| **Target Cap.**    | `inbound-goods-receipt`                       |
| **Est. Effort**    | 4 Hours                                       |
| **Risk Level**     | Medium                                        |

## Why
Pada arsitektur Two-Tier ERP, proses pengadaan barang (*procurement*) diinisiasi dan disetujui di sistem SAP Upper Line dalam bentuk pesanan pembelian (*Purchase Order*). Agar staf operasional gudang di Odoo WMS dapat mempersiapkan penerimaan fisik barang dari pemasok tanpa perlu menginput ulang data secara manual yang memakan waktu dan rentan terhadap kesalahan manusia (*human error*), sistem WMS memerlukan antarmuka otomatis untuk menerima pesanan pembelian tersebut langsung dari SAP. Oleh karena itu, diperlukan endpoint REST API resmi `/api/sap/inbound/po` yang terotentikasi, idempoten (*idempotent receipt creation*), mampu memvalidasi kode vendor dan material SAP, secara otomatis menerbitkan dokumen penerimaan (*Stock Picking Receipts*) dan baris perpindahan stok (*Stock Move*), mengonfirmasi status ke *Assigned / Ready*, serta merekam seluruh jejak audit transaksi ke dalam model `sap.sync.log`.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.2, 3.2, 3.5.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 3 (Kapabilitas 3.1).

## What Changes
Perubahan mencakup penambahan endpoint REST API JSON untuk pesanan pembelian, pemetaan data vendor dan material, pembuatan dokumen picking beserta baris item, dan pencatatan audit log transaksi:
- **Backend (ORM & Models):** Menggunakan model yang sudah ada (`stock.picking`, `stock.move`, `stock.picking.type`, `stock.location`, `res.partner`, `product.product`, `product.template`, `sap.sync.log`) untuk mencocokkan mitra berdasarkan `sap_partner_code`, produk berdasarkan `sap_material_code`, serta membuat record `stock.picking` (dengan tipe operasi `incoming`) dan record `stock.move` untuk setiap item barang.
- **Security & Access Rights:** Menerapkan otentikasi berbasis token API (`X-Odoo-API-Key` atau `Authorization: Bearer <token>`) yang divalidasi terhadap konfigurasi sistem `wms_sap_connector.sap_api_token`. Request tanpa token valid ditolak dengan status HTTP 401 Unauthorized. Eksekusi ORM dijalankan menggunakan hak administratif terisolasi (`sudo()`).
- **Views & UI:** Tidak ada view baru yang ditambahkan. Dokumen penerimaan yang diterbitkan otomatis langsung dapat dilihat pada menu operasional *Transfers* / *Receipts* dengan nomor referensi dokumen SAP terisi.
- **Integration & API:** Memperluas modul controller pada `addons/wms_sap_connector/controllers/main.py` dengan menambahkan rute `POST /api/sap/inbound/po` bertipe JSON. Endpoint menerima payload PO, mengeksekusi logika idempoten berdasarkan `sap_doc_number`, menghasilkan dokumen penerimaan stok berstatus `assigned`, mengembalikan respons HTTP 201 Created terstruktur, dan mencatat transaksi ke `sap.sync.log` dengan tipe `inbound_po`.

## Capabilities
### New Capabilities
- `None`

### Modified Capabilities
- `inbound-goods-receipt`: Menambahkan kemampuan penerimaan otomatis pesanan pembelian (*Purchase Order*) dari SAP melalui REST API `/api/sap/inbound/po`, validasi vendor dan SKU material, serta pembuatan dokumen Stock Picking Inbound dan Stock Move secara idempoten.

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `None`
- **Files to Modify:**
  - `addons/wms_sap_connector/controllers/main.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 2.2.2, 3.2, 3.5.2)
  - `docs/roadmap.md` (Fase 3, Kapabilitas 3.1)
- **Estimated Effort:** 4 jam.
- **Complexity & Risk Analysis:** Risiko tingkat menengah (Medium). Risiko payload invalid, vendor atau material tidak terdaftar dimitigasi dengan validasi skema ketat, pencarian berbasis indeks B-Tree, dan pencatatan audit log `failed` saat terjadi eksepsi.

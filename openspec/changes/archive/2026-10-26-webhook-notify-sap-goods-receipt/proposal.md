# Proposal: Webhook Notify SAP Goods Receipt

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | webhook-notify-sap-goods-receipt              |
| **Roadmap Phase**  | Fase 3: Alur Barang Masuk & Penempatan Rak (Inbound & Putaway) |
| **Target Cap.**    | `inbound-sap-webhook`                         |
| **Est. Effort**    | 3 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Dalam integrasi sistem logistik dua tingkat (*Two-Tier WMS*), setelah staf operasional gudang selesai melakukan pemeriksaan fisik, pemindaian barcode, dan penempatan barang ke rak (*Putaway*), dokumen penerimaan barang (*Stock Receipt*) divalidasi menjadi selesai (*Done*). Sistem WMS Odoo harus secara otomatis mengirimkan sinyal konfirmasi penerimaan barang (*Goods Receipt / GR*) kembali ke sistem SAP Upper Line melalui webhook HTTP POST. Konfirmasi ini krusial agar SAP dapat segera membukukan jurnal akuntansi persediaan dan hutang dagang (*General Ledger*), memutakhirkan status pesanan pembelian, serta menjaga konsistensi finansial antara operasional gudang dan kantor pusat tanpa memerlukan entri ganda manual (*double-entry*).
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.2, 3.5.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 3 (Kapabilitas 3.2).

## What Changes
Perubahan mencakup otomatisasi pengiriman webhook konfirmasi Goods Receipt saat dokumen transfer masuk divalidasi, penanganan respon simulasi jurnal akuntansi SAP ke audit log, serta penyediaan tombol pengiriman ulang manual:
- **Backend (ORM & Models):**
  - Meng-override method penyelesaian transfer (`_action_done` atau `button_validate`) pada model `stock.picking` untuk mendeteksi dokumen masuk (*incoming receipt*) yang memiliki `sap_doc_number`.
  - Menerbitkan permintaan HTTP POST ke endpoint webhook SAP (`{sap_base_url}/api/sap/goods-receipt`) dengan muatan payload standar: `sap_doc_number`, `status: "GOODS_RECEIVED"`, `received_date`, dan `warehouse_code`.
  - Menangkap respon simulasi jurnal akuntansi SAP (`sap_accounting_log`) dan mendokumentasikannya ke tabel audit `sap.sync.log` dengan arah `outbound` dan status `success`/`failed`.
  - Memperbarui field `sap_sync_status` pada dokumen picking menjadi `synced` jika sukses atau `failed` jika terjadi kendala koneksi.
  - Menambahkan method `action_send_sap_goods_receipt_webhook()` untuk memfasilitasi pengiriman ulang (*retry*) jika transmisi sebelumnya mengalami kegagalan.
- **Security & Access Rights:**
  - Memastikan method pengiriman webhook dan retry dapat diakses secara aman oleh peran `Warehouse Operator` (`group_wms_operator`) dan `Warehouse Manager` (`group_wms_manager`).
- **Views & UI:**
  - Menambahkan tombol aksi "Send SAP Webhook" / "Retry SAP Sync" pada header formulir `stock.view_picking_form` yang tampil ketika dokumen incoming berstatus `done` dan status sinkronisasi belum `synced`.
- **Integration & API:**
  - Menangani komunikasi HTTP keluar menggunakan library Python `requests` dengan *timeout* terukur (misal 10 detik) dan penanganan *resilient exception* agar kegagalan jaringan ke SAP tidak menggagalkan (*non-blocking*) validasi fisik barang di Odoo.

## Capabilities
### New Capabilities
- `inbound-sap-webhook`: Transmisi sinyal konfirmasi Goods Receipt (GR) otomatis via webhook HTTP POST ke SAP Upper Line saat dokumen penerimaan divalidasi 'Done', serta pencatatan respon jurnal akuntansi SAP ke audit log.

### Modified Capabilities
- `None`

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/tests/test_webhook_goods_receipt.py`
- **Files to Modify:**
  - `addons/wms_sap_connector/constants.py`
  - `addons/wms_sap_connector/models/stock_picking.py`
  - `addons/wms_sap_connector/views/stock_picking_views.xml`
  - `addons/wms_sap_connector/tests/__init__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 2.2.2, 3.5.2)
  - `docs/roadmap.md` (Fase 3, Kapabilitas 3.2)
- **Estimated Effort:** 3 jam.
- **Complexity & Risk Analysis:** Rendah (Low). Pengiriman webhook didesain secara *non-blocking* (*fail-safe*); jika server SAP offline atau mengalami timeout, transfer barang fisik di gudang tetap tersimpan dengan status Done, dokumen ditandai `failed`, dan operator/manajer dapat mengirim ulang kapan saja melalui tombol retry.

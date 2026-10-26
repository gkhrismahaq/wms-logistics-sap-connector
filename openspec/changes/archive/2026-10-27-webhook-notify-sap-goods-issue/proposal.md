# Proposal: Webhook Notify SAP Goods Issue

| Field              | Value                                                              |
|--------------------|--------------------------------------------------------------------|
| **Change Name**    | webhook-notify-sap-goods-issue                                     |
| **Roadmap Phase**  | Fase 4: Alur Pengantaran, Armada & Bukti Serah Terima (Outbound & Delivery) |
| **Target Cap.**    | `proof-of-delivery-pod`                                            |
| **Est. Effort**    | 4 Hours                                                            |
| **Risk Level**     | Medium                                                             |

## Why
Dalam arsitektur *Two-Tier ERP* antara Odoo WMS dan SAP Upper Line, siklus akhir proses pengeluaran logistik (*outbound dispatch*) belum dianggap tuntas secara akuntansi finansial sebelum kargo benar-benar diserahkan kepada pihak penerima dan bukti serah terima (*Proof of Delivery* / POD) terverifikasi lengkap. Setelah dokumen pengantaran divalidasi dan bukti POD tersedia (`has_pod == True`), sistem Odoo wajib memberitahukan SAP secara *real-time* melalui webhook HTTP POST *Goods Issue (GI)* (`POST /api/sap/goods-issue`). Transmisi ini memicu SAP untuk mencatatkan pemotongan persediaan secara finansial, membukukan jurnal pemotongan Harga Pokok Penjualan (HPP), serta mengembalikan respons simulasi akuntansi (`sap_accounting_log`) yang harus direkam ke dalam `sap.sync.log` demi integritas audit dan rekonsiliasi.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.3 & 3.5.3 dan [roadmap.md](../../docs/roadmap.md) — Fase 4.3.

## What Changes
- **Backend (ORM & Models):**
  - Menambahkan konstanta baru pada `addons/wms_sap_connector/constants.py`: `REF_PREFIX_GOODS_ISSUE = "GI"`, `SAP_ENDPOINT_GOODS_ISSUE = "/api/sap/goods-issue"`, dan `WEBHOOK_STATUS_GOODS_ISSUED = "GOODS_ISSUED"`.
  - Memperluas model `stock.picking` dengan method internal `_send_sap_goods_issue_webhook()` yang memformat payload JSON Goods Issue, menembak endpoint SAP via HTTP POST terotentikasi, memutakhirkan `sap_sync_status`, serta merekam audit transaksi ke `sap.sync.log`.
  - Memperluas pemanggilan otomatis pada `_action_done()` untuk dokumen transfer pengeluaran (`outgoing`) yang memiliki `sap_doc_number` dan telah memiliki POD valid (`has_pod == True`).
  - Menambahkan *listener* pada method `write()` saat field bukti POD (`proof_of_delivery` / `pod_signed_by`) diperbarui pada transfer yang sudah berstatus `done` agar webhook dapat tertrigger secara otomatis.
  - Menambahkan method aksi manual `action_send_sap_goods_issue_webhook()` untuk kebutuhan pengiriman ulang (*retry*) transaksi yang gagal secara independen.
- **Security & Access Rights:**
  - Memastikan tombol aksi pengiriman ulang Goods Issue dapat diakses oleh peran Dispatcher Logistik dan Warehouse Manager sesuai aturan hak akses grup `stock.group_stock_user` dan `stock.group_stock_manager`.
- **Views & UI:**
  - Menambahkan tombol aksi `"Send Goods Issue to SAP"` pada header formulir `stock.view_picking_form` khusus untuk transfer bertipe `outgoing`, berstatus `done`, dan memiliki nomor referensi `sap_doc_number`.
- **Integration & API:**
  - Protokol transmisi webhook HTTP POST `POST /api/sap/goods-issue` ke server SAP/FastAPI dengan *bearer token* atau API key header (`X-Odoo-API-Key`).
  - Penanganan respons JSON sukses (kode HTTP 200/201) berisi simulasi jurnal akuntansi HPP (`sap_accounting_log`), serta penanganan *fail-safe* jika koneksi gagal atau timeout tanpa membatalkan mutasi stok fisik di Odoo.

## Capabilities
### New Capabilities
- `None`

### Modified Capabilities
- `proof-of-delivery-pod`: Penambahan transmisi webhook konfirmasi Goods Issue (GI) ke SAP saat dokumen pengantaran berstatus Done dan verifikasi bukti POD telah lengkap (`has_pod == True`), serta pencatatan respons simulasi jurnal pemotongan HPP ke `sap.sync.log`.

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/tests/test_webhook_goods_issue.py`
- **Files to Modify:**
  - `addons/wms_sap_connector/constants.py`
  - `addons/wms_sap_connector/models/stock_picking.py`
  - `addons/wms_sap_connector/views/stock_picking_views.xml`
  - `addons/wms_sap_connector/tests/__init__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 2.2.3, 3.2, 3.5.3)
  - `docs/roadmap.md` (Capability 4.3: `proof-of-delivery-pod`)
- **Estimated Effort:** 4 jam.
- **Complexity & Risk Analysis:** Risiko kegagalan jaringan eksternal atau server SAP sedang *downtime*. Mitigasi dilakukan dengan menerapkan eksekusi *fail-safe* (*non-blocking try-except*), pencatatan status `failed` ke `sap.sync.log` dan `stock.picking`, serta penyediaan tombol *retry manual* di UI.

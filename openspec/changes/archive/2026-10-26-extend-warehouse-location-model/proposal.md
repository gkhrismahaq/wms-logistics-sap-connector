# Proposal: Extend Warehouse Location Model

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | extend-warehouse-location-model               |
| **Roadmap Phase**  | Fase 2: Perluasan Master Data & Sinkronisasi (Master Data) |
| **Target Cap.**    | `master-data-models`                          |
| **Est. Effort**    | 3 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Dalam integrasi pergudangan Two-Tier ERP antara Odoo 17 dan SAP, sistem SAP mengorganisasikan struktur logistik berbasis Plant (Pabrik/Unit Operasional) dan Storage Location (SLoc / Gudang Penyimpanan). Dokumen transaksi perpindahan barang dari SAP (seperti Purchase Order Inbound dan Sales Delivery Outbound) merujuk pada kode Plant dan SLoc tersebut. Selain itu, staf gudang di lapangan memerlukan identifikasi rak fisik berbasis barcode (`barcode`) untuk mendukung pemindaian cepat pada proses alokasi penempatan barang (*putaway*) maupun pengambilan (*picking*). Agar WMS Odoo 17 dapat memetakan lokasi fisik rak dan zona simpan terhadap kode hierarki logistik SAP secara akurat, model `stock.location` perlu diperluas dengan field `sap_plant_code`, `sap_sloc_code`, dan `barcode`.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 2 (Kapabilitas 2.1).

## What Changes
Perubahan mencakup penambahan atribut pemetaan logistik SAP dan kode barcode rak pada model lokasi stok, penyajian field pada tampilan form lokasi Odoo, serta penyiapan indeks database:
- **Backend (ORM & Models):** Mewarisi model `stock.location` pada `addons/wms_sap_connector/models/stock_location.py` dengan menambahkan bidang `sap_plant_code` (Char, `index=True`), `sap_sloc_code` (Char, `index=True`), dan memastikan `barcode` (Char, `index=True`, `copy=False`) terkonfigurasi optimal untuk pemindaian fisik. Mendaftarkan file model ke dalam file inisialisasi `addons/wms_sap_connector/models/__init__.py`.
- **Security & Access Rights:** Mengikuti arsitektur sekuriti standar Odoo `stock`. Staf operasional gudang (`stock.group_stock_user`) memiliki hak baca untuk membaca lokasi dan memindai barcode, sedangkan Kepala Gudang / Administrator (`stock.group_stock_manager`) memiliki hak penuh untuk mengonfigurasi pemetaan Plant dan Storage Location SAP.
- **Views & UI:** Mewarisi tampilan Form Lokasi `stock.view_location_form` pada `addons/wms_sap_connector/views/stock_location_views.xml` dengan menambahkan grup khusus integrasi SAP (`sap_plant_code`, `sap_sloc_code`) serta memastikan field `barcode` ditampilkan secara jelas pada formulir lokasi. Mendaftarkan file XML view ke dalam manifest `addons/wms_sap_connector/__manifest__.py`.
- **Integration & API:** Field `sap_plant_code` dan `sap_sloc_code` diindeks (`index=True`) guna mempercepat kueri pencocokan lokasi penyimpanan saat modul menerima payload transaksi barang masuk (*Goods Receipt*) maupun penempatan otomatis (*Putaway Rule*) dari SAP.

## Capabilities
### New Capabilities
- `None`

### Modified Capabilities
- `master-data-models`: Penambahan requirement baru `[REQ-MD-03]` untuk perluasan model lokasi gudang (`stock.location`) dengan kode mapping SAP (`sap_plant_code`, `sap_sloc_code`) dan identifikasi barcode rak fisik (`barcode`).

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/models/stock_location.py`
  - `addons/wms_sap_connector/views/stock_location_views.xml`
- **Files to Modify:**
  - `addons/wms_sap_connector/models/__init__.py`
  - `addons/wms_sap_connector/__manifest__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 3.2)
  - `docs/roadmap.md` (Kapabilitas 2.1)
- **Estimated Effort:** 3 jam.
- **Complexity & Risk Analysis:** Kompleksitas dan risiko rendah (Low). Implementasi memanfaatkan pewarisan ORM standar Odoo (`_inherit = 'stock.location'`) tanpa mengubah integritas perhitungan kuantitas persediaan bawaan modul `stock`.

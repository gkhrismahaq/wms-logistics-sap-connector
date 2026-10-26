# Implementation Tasks: Automate Putaway Bin Allocation

<!-- STRICT RULES:
1. Every task MUST use format: - [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}
2. Domain tag MUST be one of: [Backend], [Security], [UI], [Integration], [Test]
3. MUST specify target file path in backticks (`addons/...`)
4. Task duration MUST NOT exceed 2 hours per item.
5. Strictly follow phase order: Foundation/Model -> Security -> UI -> Logic/API -> Verification.
-->

## 1. Data Model & Backend Foundation

- [x] 1.1 [Backend] Buat file konfigurasi data seed aturan penempatan putaway (`stock.putaway.rule`) untuk material SAP pada `addons/wms_sap_connector/data/stock_putaway_data.xml`
- [x] 1.2 [Backend] Daftarkan file data seed `data/stock_putaway_data.xml` ke dalam manifest modul pada `addons/wms_sap_connector/__manifest__.py`

## 2. Security & Access Control

- [x] 2.1 [Security] Daftarkan aturan hak akses model `stock.putaway.rule` untuk grup `group_wms_operator` (Read-only) dan `group_wms_manager` (Full CRUD) pada `addons/wms_sap_connector/security/ir.model.access.csv`

## 3. User Interface & Views

- [x] 3.1 [UI] Pastikan visibilitas kolom lokasi rak tujuan (`location_dest_id`) pada tab Operations dan Detailed Operations formulir picking pada `addons/wms_sap_connector/views/stock_picking_views.xml`

## 4. Business Logic & Integration Endpoints

- [x] 4.1 [Backend] Integrasikan dan validasi evaluasi resolusi aturan putaway otomatis pada method `create_inbound_from_sap` di `addons/wms_sap_connector/models/stock_picking.py`
- [x] 4.2 [Integration] Verifikasi alokasi rak spesifik pada baris `stock.move.line` yang diterbitkan melalui endpoint REST API inbound PO pada `addons/wms_sap_connector/controllers/main.py`

## 5. Verification & Testing

- [x] 5.1 [Test] Jalankan uji validasi sintaks XML dan Python modul pada `addons/wms_sap_connector/` serta upgrade modul via `make addon wms_sap_connector`
- [x] 5.2 [Test] Uji skenario alokasi rak putaway otomatis (`REQ-INB-06`) untuk produk terpetakan (`Shelf 1`) dan fallback lokasi induk untuk produk tanpa aturan khusus
- [x] 5.3 [Test] Uji skenario visibilitas antarmuka dan kontrol hak akses putaway rule (`REQ-INB-07`) untuk operator gudang

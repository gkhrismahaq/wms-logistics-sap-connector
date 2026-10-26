# Implementation Tasks: Report Official Surat Jalan

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Telaah ketersediaan field relasi dan komputasi muatan pada `stock.picking` (`vehicle_id`, `driver_id`, `total_weight`, `total_volume`, `sap_doc_number`) di `addons/wms_sap_connector/models/stock_picking.py`.
- [x] 1.2 [Backend] Verifikasi integrasi field produk material SAP (`sap_material_code`) pada `stock.move` di `addons/wms_sap_connector/models/product_template.py` untuk pemetaan baris kargo surat jalan.

## 2. Security & Access Control
- [x] 2.1 [Security] Pastikan grup pengguna Dispatcher (`group_wms_dispatcher`), Operator (`group_wms_operator`), dan Manager (`group_wms_manager`) memiliki hak akses baca dan cetak laporan `stock.picking` pada `addons/wms_sap_connector/security/security.xml` dan `addons/wms_sap_connector/security/ir.model.access.csv`.

## 3. User Interface & Views
- [x] 3.1 [UI] Buat berkas definisi action laporan `ir.actions.report` dan template QWeb PDF dokumen Surat Jalan pada `addons/wms_sap_connector/report/report_surat_jalan.xml`.
- [x] 3.2 [UI] Tambahkan tombol aksi cepat "Print Surat Jalan" pada header form view transfer pengeluaran barang di `addons/wms_sap_connector/views/stock_picking_views.xml`.
- [x] 3.3 [Backend] Daftarkan file laporan `report/report_surat_jalan.xml` ke dalam daftar `data` pada manifes modul di `addons/wms_sap_connector/__manifest__.py`.

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [UI] Implementasikan template detail `report_surat_jalan_document` yang memuat kop DC Lowokwaru, barcode Code128 native Odoo, data pelanggan tujuan, rincian armada/supir, dan ringkasan muatan di `addons/wms_sap_connector/report/report_surat_jalan.xml`.
- [x] 4.2 [UI] Implementasikan tabel rincian baris kargo dan 3 blok kolom pengesahan tanda tangan fisik (Prepared By, Delivered By, Received By) dengan penanganan fallback nilai kosong pada `addons/wms_sap_connector/report/report_surat_jalan.xml`.

## 5. Verification & Testing
- [x] 5.1 [Test] Buat berkas unit test otomatis `addons/wms_sap_connector/tests/test_report_surat_jalan.py` dan daftarkan pada `addons/wms_sap_connector/tests/__init__.py` untuk menguji rendering action report dan integritas data QWeb PDF.
- [x] 5.2 [Test] Lakukan kompilasi Python (`py_compile`) dan upgrade modul pada container Docker via `make addon wms_sap_connector` memastikan log bersih tanpa peringatan.
- [x] 5.3 [Test] Jalankan seluruh rangkaian automated unit test Odoo (`test_report_surat_jalan.py` dan regresi keseluruhan) untuk memvalidasi pemenuhan skenario `[REQ-OUT-06]` pada `spec.md`.

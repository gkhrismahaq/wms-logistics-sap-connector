# Implementation Tasks: Feature Driver Proof of Delivery

## 1. Data Model & Backend Foundation
- [x] 1.1 [Backend] Deklarasikan field bukti serah terima digital `proof_of_delivery`, `pod_signed_by`, `pod_timestamp`, dan `has_pod` pada model `stock.picking` di `addons/wms_sap_connector/models/stock_picking.py`.
- [x] 1.2 [Backend] Implementasikan metode komputasi `@api.depends('proof_of_delivery', 'pod_signed_by') def _compute_has_pod(self)` pada `stock.picking` di `addons/wms_sap_connector/models/stock_picking.py`.

## 2. Security & Access Control
- [x] 2.1 [Security] Verifikasi hak akses baca dan tulis pada model `stock.picking` untuk grup `group_wms_dispatcher`, `group_wms_operator`, dan `group_wms_manager` pada `addons/wms_sap_connector/security/security.xml` dan `addons/wms_sap_connector/security/ir.model.access.csv`.

## 3. User Interface & Views
- [x] 3.1 [UI] Tambahkan halaman notebook khusus "Proof of Delivery (POD)" (`page_proof_of_delivery`) pada form view `stock.view_picking_form` dengan widget pratinjau gambar di `addons/wms_sap_connector/views/stock_picking_views.xml`.
- [x] 3.2 [UI] Tambahkan kolom `pod_signed_by` dan `pod_timestamp` pada tree view `vpicktree_inherit_sap` di `addons/wms_sap_connector/views/stock_picking_views.xml`.
- [x] 3.3 [UI] Tambahkan filter pencarian cepat "Has POD" dan "Missing POD" pada search view `view_picking_internal_search_inherit_sap` di `addons/wms_sap_connector/views/stock_picking_views.xml`.

## 4. Business Logic & Integration Endpoints
- [x] 4.1 [Backend] Implementasikan otomatisasi `@api.onchange('proof_of_delivery', 'pod_signed_by')` untuk menetapkan `pod_timestamp` ke waktu saat ini jika kosong pada `addons/wms_sap_connector/models/stock_picking.py`.
- [x] 4.2 [Backend] Terapkan logika fallback pada metode `write()` di `stock.picking` pada `addons/wms_sap_connector/models/stock_picking.py` untuk menjamin `pod_timestamp` terisi saat update via ORM/API jika belum ditentukan.

## 5. Verification & Testing
- [x] 5.1 [Test] Buat berkas unit test otomatis `addons/wms_sap_connector/tests/test_proof_of_delivery.py` dan daftarkan pada `addons/wms_sap_connector/tests/__init__.py` untuk menguji atribut POD, otomatisasi timestamp, filter, dan komputasi `has_pod`.
- [x] 5.2 [Test] Lakukan kompilasi Python (`py_compile`) dan upgrade modul pada container Docker via `make addon wms_sap_connector` memastikan log bersih tanpa peringatan.
- [x] 5.3 [Test] Jalankan seluruh rangkaian automated unit test Odoo (`test_proof_of_delivery.py` dan regresi keseluruhan) untuk memvalidasi pemenuhan skenario `[REQ-POD-01]` dan `[REQ-POD-02]` pada `spec.md`.

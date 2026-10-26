# Proposal: Extend Picking Dispatch Fields

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | extend-picking-dispatch-fields                |
| **Roadmap Phase**  | Fase 4: Alur Pengantaran, Armada & Bukti Serah Terima (Outbound & Delivery) |
| **Target Cap.**    | `outbound-dispatch-surat-jalan`               |
| **Est. Effort**    | 3 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Setelah dokumen Delivery Order (`outgoing`) berhasil dibuat dari integrasi SAP, staf logistik (Dispatcher) membutuhkan fasilitas untuk menetapkan armada kendaraan fisik (`vehicle_id`) dan supir pengantar (`driver_id`) yang bertanggung jawab, serta memantau kalkulasi total berat muatan (`total_weight`) dan total volume kubikasi kargo (`total_volume`) secara akurat guna mencegah kelebihan beban (*overcapacity*) sebelum formulir resmi Surat Jalan dicetak.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 4.2.

## What Changes
Perubahan ini menambahkan field penugasan operasional pengantaran dan kalkulasi kapasitas pada dokumen transfer Odoo 17:
- **Backend (ORM & Models):**
  - Memperluas model `stock.picking` di `addons/wms_sap_connector/models/stock_picking.py`:
    - Menambahkan Many2one `vehicle_id` merujuk ke model `wms.vehicle` (dengan domain armada aktif/tersedia).
    - Menambahkan Many2one `driver_id` merujuk ke model `res.partner` (dengan domain individu `is_company = False`).
    - Menambahkan mekanisme otomatisasi onchange: saat `vehicle_id` dipilih dan memiliki supir penanggung jawab (`vehicle_id.driver_id`), nilai `driver_id` otomatis terisi.
    - Menambahkan field terkomputasi `total_weight` (Float, kg) dan `total_volume` (Float, m³) dengan decorator `@api.depends('move_ids.product_id.weight', 'move_ids.product_id.volume', 'move_ids.product_uom_qty')` dan `store=True`.
    - Menambahkan validasi kapasitas armada: memunculkan peringatan atau memvalidasi batasan muatan bila `total_weight` melebihi `vehicle_id.max_weight` atau `total_volume` melebihi `vehicle_id.max_volume` (saat kapasitas > 0).
- **Security & Access Rights:**
  - Memastikan hak akses read/write field dispatch baru pada `stock.picking` dapat diakses secara tepat oleh Logistics Dispatcher (`group_wms_dispatcher`) dan Warehouse Manager (`group_wms_manager`).
- **Views & UI:**
  - Memperbarui `addons/wms_sap_connector/views/stock_picking_views.xml` untuk menyajikan group informasi pengantaran (*Dispatch & Fleet Information*) pada form view `stock.view_picking_form` serta menambahkan kolom armada `vehicle_id` pada tree view `vpicktree_inherit_sap`.
- **Integration & API:**
  - Tidak ada endpoint API baru yang dibuat. Data armada dan supir yang telah ditetapkan akan digunakan oleh pelaporan cetak Surat Jalan (`report-official-surat-jalan`) dan bukti serah terima POD (`proof-of-delivery-pod`).

## Capabilities
### New Capabilities
- `None`

### Modified Capabilities
- `outbound-dispatch-surat-jalan`: Menambahkan spesifikasi penetapan armada kargo dan supir pengantar pada Delivery Order (`stock.picking`), serta kalkulasi otomatis total berat dan volume kargo dengan validasi kapasitas muatan.

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/tests/test_picking_dispatch_fields.py`
- **Files to Modify:**
  - `addons/wms_sap_connector/models/stock_picking.py`
  - `addons/wms_sap_connector/views/stock_picking_views.xml`
  - `addons/wms_sap_connector/tests/__init__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 3.2)
  - `docs/roadmap.md` (Capability 4.2)
- **Estimated Effort:** 3 jam.
- **Complexity & Risk Analysis:** Rendah. Implementasi mengandalkan fitur relasional dan komputasi standar Odoo ORM yang aman tanpa memodifikasi core lifecycle picking Odoo.

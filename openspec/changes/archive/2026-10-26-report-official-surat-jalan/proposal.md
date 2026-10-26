# Proposal: Report Official Surat Jalan

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | report-official-surat-jalan                   |
| **Roadmap Phase**  | Fase 4: Alur Pengantaran, Armada & Bukti Serah Terima (Outbound & Delivery) |
| **Target Cap.**    | `outbound-dispatch-surat-jalan`               |
| **Est. Effort**    | 3 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Setiap pengiriman barang kargo dari Distribution Center (DC Lowokwaru) menuju jaringan toko retail dan pelanggan wajib disertai dokumen fisik resmi Surat Jalan (*Delivery Slip*) sebagai dokumen legalitas transportasi di jalan raya, bukti sah perpindahan kepemilikan barang sementara, serta media pembubuhan tanda tangan serah terima fisik sebelum pencatatan digital POD diunggah ke sistem.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 1.3 dan [roadmap.md](../../docs/roadmap.md) — Fase 4.2.

## What Changes
Perubahan ini menambahkan kemampuan pencetakan dokumen resmi Surat Jalan berformat QWeb PDF pada dokumen Delivery Order Odoo 17:
- **Backend (ORM & Models):**
  - Menggunakan struktur data yang sudah tersedia pada model `stock.picking`, `stock.move`, `wms.vehicle`, dan `res.partner` tanpa memerlukan mutasi field baru.
- **Security & Access Rights:**
  - Memastikan action cetak laporan dapat diakses dan dieksekusi secara mulus oleh pengguna dengan hak akses Logistics Dispatcher (`group_wms_dispatcher`), Warehouse Operator (`group_wms_operator`), dan Warehouse Manager (`group_wms_manager`).
- **Views & UI:**
  - Membuat berkas template laporan QWeb PDF di `addons/wms_sap_connector/report/report_surat_jalan.xml` yang mencakup:
    - Kop surat identitas fasilitas logistik (Madura Mart / DC Lowokwaru).
    - Barcode Code128 referensi dokumen transfer (`picking.name`) dan nomor referensi pesanan SAP (`sap_doc_number`).
    - Informasi pelanggan dan alamat lengkap tujuan pengantaran (`partner_id`).
    - Rincian penugasan armada kendaraan (`vehicle_id.license_plate`) dan supir pengantar (`driver_id.name`).
    - Ringkasan akumulasi muatan (`total_weight` kg dan `total_volume` m³).
    - Tabel rincian kargo produk (Nomor, Kode SKU/SAP, Nama Barang, Kuantitas, dan Satuan UoM).
    - Area legalitas 3 kolom tanda tangan: Petugas Gudang / Dispatcher (*Prepared By*), Supir Pengantar (*Delivered By*), dan Penerima Toko (*Received By*).
  - Mendaftarkan `ir.actions.report` yang terikat pada menu Print dokumen `stock.picking`.
  - Menambahkan tombol cetak cepat "Print Surat Jalan" pada header form view `stock.view_picking_form` di `addons/wms_sap_connector/views/stock_picking_views.xml`.
  - Mendaftarkan file XML laporan pada `addons/wms_sap_connector/__manifest__.py`.
- **Integration & API:**
  - Tidak ada endpoint API baru. Laporan mencetak data pengantaran yang diterbitkan dari integrasi SAP Upper Line.

## Capabilities
### New Capabilities
- `None`

### Modified Capabilities
- `outbound-dispatch-surat-jalan`: Menambahkan spesifikasi penerbitan dan pencetakan dokumen fisik resmi Surat Jalan Pengantaran Barang (*Official Delivery Slip*) berbasis QWeb PDF dengan barcode terstandarisasi.

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/report/report_surat_jalan.xml`
  - `addons/wms_sap_connector/tests/test_report_surat_jalan.py`
- **Files to Modify:**
  - `addons/wms_sap_connector/__manifest__.py`
  - `addons/wms_sap_connector/views/stock_picking_views.xml`
  - `addons/wms_sap_connector/tests/__init__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 1.3)
  - `docs/roadmap.md` (Capability 4.2)
- **Estimated Effort:** 3 jam.
- **Complexity & Risk Analysis:** Rendah. Implementasi mengikuti arsitektur QWeb reporting standar Odoo 17 yang didukung penuh oleh wkhtmltopdf binary.

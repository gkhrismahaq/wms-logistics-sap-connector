# Proposal: Feature Driver Proof of Delivery

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | `feature-driver-proof-of-delivery`            |
| **Roadmap Phase**  | Fase 4: Alur Pengantaran, Armada & Bukti Serah Terima (Outbound & Delivery) |
| **Target Cap.**    | `proof-of-delivery-pod`                       |
| **Est. Effort**    | 3 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Penyerahan kargo fisik kepada pelanggan di toko retail (misalnya Madura Mart / Alfamart) membutuhkan bukti legal serah terima digital yang dapat diverifikasi secara transparan. Tanpa pencatatan Proof of Delivery (POD) yang valid (berkas foto serah terima fisik atau tanda tangan digital, nama terang penerima, dan timestamp penyerahan), pengantaran kargo rentan terhadap sengketa penerimaan barang, serta sistem tidak memiliki dasar verifikasi yang kuat sebelum memicu konfirmasi *Goods Issue (GI)* ke SAP Upper Line untuk pemotongan nilai buku inventori.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.3, 3.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 4.3.

## What Changes
Perubahan ini menambahkan kemampuan pencatatan dan pengelolaan bukti serah terima barang (*Proof of Delivery / POD*) secara digital pada dokumen pengeluaran barang (`stock.picking` bertipe `outgoing`):
- **Backend (ORM & Models):**
  - Memperluas model `stock.picking` dengan field bukti serah terima:
    - `proof_of_delivery` (Binary, `attachment=True`): Berkas gambar pindaian tanda tangan atau foto bukti penerimaan fisik barang.
    - `pod_signed_by` (Char): Nama terang pihak penerima di lokasi tujuan.
    - `pod_timestamp` (Datetime): Waktu pencatatan bukti penyerahan barang (terisi otomatis saat berkas/nama penerima dicatat jika kosong).
    - `has_pod` (Boolean, compute & stored): Penanda ketersediaan bukti serah terima untuk kemudahan pelaporan dan audit operasional.
- **Security & Access Rights:**
  - Memastikan grup pengguna Dispatcher (`group_wms_dispatcher`), Operator (`group_wms_operator`), dan Manager (`group_wms_manager`) memiliki hak akses untuk memperbarui dan memeriksa data POD pada dokumen pengantaran.
- **Views & UI:**
  - Menambahkan tab khusus "Proof of Delivery (POD)" pada form view `stock.view_picking_form` di `addons/wms_sap_connector/views/stock_picking_views.xml` (tampil dinamis hanya pada transfer pengeluaran barang `picking_type_code == 'outgoing'`).
  - Menampilkan widget gambar (`widget="image"`) untuk preview foto/tanda tangan bukti POD secara interaktif.
  - Memperluas tree view `vpicktree_inherit_sap` dengan kolom `pod_signed_by` dan `pod_timestamp` (opsional disembunyikan/ditampilkan).
  - Menambahkan filter pencarian pada search view `stock_picking_views.xml` untuk menyaring dokumen yang sudah memiliki POD ("Has POD") dan yang belum melampirkan POD ("Missing POD").
- **Integration & API:**
  - Tidak ada endpoint API baru pada change ini. Validitas data POD ini menjadi prasyarat bagi change berikutnya (`webhook-notify-sap-goods-issue`) untuk menembakkan sinyal penyelesaian kargo ke SAP Upper Line.

## Capabilities
### New Capabilities
- `proof-of-delivery-pod`: Pencatatan dan validasi bukti penyerahan barang kargo di lokasi tujuan secara digital berupa berkas gambar bukti serah terima, nama terang penerima, dan timestamp waktu penyerahan pada dokumen pengeluaran barang.

### Modified Capabilities
- `None`

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/tests/test_proof_of_delivery.py`
- **Files to Modify:**
  - `addons/wms_sap_connector/models/stock_picking.py`
  - `addons/wms_sap_connector/views/stock_picking_views.xml`
  - `addons/wms_sap_connector/tests/__init__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 2.2.3, 3.2)
  - `docs/roadmap.md` (Capability 4.3)
- **Estimated Effort:** 3 jam.
- **Complexity & Risk Analysis:** Rendah. Implementasi menggunakan penyimpanan `attachment=True` pada field binary Odoo 17 untuk memastikan file gambar tidak membebani ukuran baris tabel database PostgreSQL.

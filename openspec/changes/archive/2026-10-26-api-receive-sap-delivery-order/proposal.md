# Proposal: API Receive SAP Delivery Order

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | api-receive-sap-delivery-order                |
| **Roadmap Phase**  | Fase 4: Alur Pengantaran, Armada & Bukti Serah Terima (Outbound & Delivery) |
| **Target Cap.**    | `outbound-dispatch-surat-jalan`               |
| **Est. Effort**    | 3 Hours                                       |
| **Risk Level**     | Medium                                        |

## Why
Dalam arsitektur Two-Tier ERP terintegrasi, transaksi penjualan pelanggan dan pengecekan batas kredit dikelola secara terpusat pada sistem SAP Upper Line. Saat pesanan penjualan disetujui, SAP merilis instruksi pengiriman kargo (*Sales Delivery Request / Order*). Sistem WMS Odoo memerlukan antarmuka REST API publik yang aman, terautentikasi, dan idempoten untuk menerima instruksi pengiriman tersebut secara real-time, mendokumentasikan jejak audit pertukaran data ke `sap.sync.log`, serta secara otomatis mengonversinya menjadi dokumen *Delivery Order* (`stock.picking` tipe `outgoing`) siap proses (*Assigned / Confirmed*). Integrasi otomatis ini mengeliminasi entri manual, mencegah keterlambatan penyiapan barang kargo di gudang, dan memastikan keselarasan data pesanan antara kantor pusat dan lantai operasional.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.3, 3.5.3 dan [roadmap.md](../../docs/roadmap.md) — Fase 4 (Kapabilitas 4.2).

## What Changes
Perubahan mencakup penyediaan endpoint REST API penerima instruksi pengiriman pesanan penjualan SAP serta logika bisnis konversi otomatis menjadi dokumen Delivery Order Odoo:
- **Backend (ORM & Models):**
  - Mengimplementasikan method bisnis `create_outbound_from_sap(payload_dict)` pada model `stock.picking`:
    - Memvalidasi keberadaan field mandatori: `sap_doc_number`, `customer_code`, dan daftar `items`.
    - Memetakan kode pelanggan SAP (`customer_code`) ke record mitra `res.partner` berdasarkan field `sap_partner_code`.
    - Menerapkan pengecekan idempoten: jika dokumen picking `outgoing` dengan nomor SAP yang sama telah tercatat, sistem mengembalikan record eksisting tanpa menerbitkan dokumen duplikat.
    - Menentukan tipe operasi picking `outgoing` (Delivery Orders gudang `DCLOW`), lokasi asal stok (*Stock Location*), dan lokasi tujuan pelanggan (*Customer Location*).
    - Menerbitkan baris pergerakan stok (`stock.move`) untuk setiap material pesanan SAP (`sap_material_code`) dan kuantitas barang (`qty`).
    - Mengonfirmasi dokumen picking (`action_confirm()` dan `action_assign()`) agar stok teralokasi dan siap untuk diproses staf gudang.
- **Security & Access Rights:**
  - Memproteksi endpoint integrasi menggunakan autentikasi API Token (`X-Odoo-API-Key` atau `Authorization: Bearer <token>`).
  - Mengeksekusi pembuatan dokumen melalui konteks `sudo()` secara terisolasi dan aman di dalam controller integrasi resmi.
- **Views & UI:**
  - Tidak ada perubahan antarmuka XML views pada change ini.
- **Integration & API:**
  - Membuat controller baru `SapOutboundController` pada `addons/wms_sap_connector/controllers/main.py`.
  - Mendaftarkan rute endpoint HTTP `POST /api/sap/outbound/delivery` dengan `auth="public"` dan proteksi CSRF non-aktif (`csrf=False`).
  - Mencatat seluruh siklus hidup transaksi (payload masuk, status keberhasilan/kegagalan, dan referensi sinkronisasi) ke dalam tabel audit `sap.sync.log` dengan tipe `outbound_so` dan arah `inbound`.
  - Mengembalikan respon standar JSON:
    - HTTP 200: Berhasil membuat Delivery Order baru atau berhasil mengembalikan dokumen idempoten.
    - HTTP 400: Validasi gagal (field hilang, customer/material tidak terdaftar).
    - HTTP 401: Kredensial API token tidak valid atau tidak disertakan.

## Capabilities
### New Capabilities
- `outbound-dispatch-surat-jalan`: Penerimaan instruksi pengiriman pesanan penjualan (Sales Delivery Order) dari SAP melalui REST API dan konversi otomatis menjadi dokumen Delivery Order (outgoing) di Odoo.

### Modified Capabilities
- `None`

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/tests/test_outbound_delivery_api.py`
- **Files to Modify:**
  - `addons/wms_sap_connector/constants.py`
  - `addons/wms_sap_connector/controllers/main.py`
  - `addons/wms_sap_connector/models/stock_picking.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 2.2.3, 3.5.3)
  - `docs/roadmap.md` (Fase 4, Kapabilitas 4.2)
- **Estimated Effort:** 3 jam.
- **Complexity & Risk Analysis:** Tingkat risiko sedang (Medium Risk) karena melibatkan pemrosesan data API eksternal dan mutasi reservasi stok barang keluar (*outgoing moves*). Mitigasi dilakukan dengan validasi ketat, pengecekan idempoten, dan pencatatan audit log komprehensif.

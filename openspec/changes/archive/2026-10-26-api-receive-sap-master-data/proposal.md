# Proposal: API Receive SAP Master Data

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | api-receive-sap-master-data                   |
| **Roadmap Phase**  | Fase 2: Perluasan Master Data & Sinkronisasi (Master Data) |
| **Target Cap.**    | `master-data-api-connector`                   |
| **Est. Effort**    | 4 Hours                                       |
| **Risk Level**     | Medium                                        |

## Why
Dalam arsitektur Two-Tier ERP, sistem SAP Upper Line bertindak sebagai sumber kebenaran tunggal (*Single Source of Truth*) untuk data master material, vendor, dan pelanggan. Agar operasional gudang Odoo 17 dapat mengeksekusi penerimaan barang pesanan pembelian (*Purchase Order*) dan pengiriman barang (*Sales Delivery*) tanpa hambatan inkonsistensi data, WMS memerlukan antarmuka otomatis untuk menerima pembaruan master data secara langsung dari SAP. Tanpa adanya endpoint penerima ini, staf gudang terpaksa melakukan input data ganda manual yang rentan kesalahan manusia (*human error*). Oleh karena itu, diperlukan endpoint REST API `/api/sap/master` yang terotentikasi, idempoten (*upsert*), mampu menangani transmisi string gambar produk Base64 ke field bawaan Odoo (`image_1920`), serta secara otomatis merekam seluruh jejak audit transaksi ke dalam model `sap.sync.log`.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 2.2.1, 3.2, 3.5.1 dan [roadmap.md](../../docs/roadmap.md) — Fase 2 (Kapabilitas 2.2).

## What Changes
Perubahan mencakup penambahan paket controller web Odoo, penanganan rute REST API JSON, validasi keamanan berbasis token, logika pemrosesan idempotent upsert untuk material, mitra, dan plant, serta pencatatan otomatis audit log:
- **Backend (ORM & Models):** Menggunakan model yang sudah ada (`product.template`, `res.partner`, `stock.location`, `sap.sync.log`) untuk operasi pencarian dan pembaruan data secara aman menggunakan ORM Odoo 17.
- **Security & Access Rights:** Menerapkan pengamanan endpoint berbasis token API (`X-Odoo-API-Key` atau `Authorization: Bearer <token>`) yang divalidasi terhadap konfigurasi sistem `wms_sap_connector.sap_api_token`. Request tanpa token valid ditolak dengan status HTTP 401 Unauthorized. Eksekusi ORM internal dijalankan menggunakan hak administratif terisolasi (`sudo()`).
- **Views & UI:** Tidak ada view baru yang ditambahkan. Record yang disinkronkan langsung dapat ditinjau melalui form/tree produk, kontak, dan dashboard `sap.sync.log`.
- **Integration & API:** Membuat modul controller `addons/wms_sap_connector/controllers/main.py` yang mengekspos endpoint `POST /api/sap/master` bertipe JSON. Endpoint menerima muatan data master (Material, Partner, Plant), mengonversi Base64 image ke biner Odoo, memvalidasi integritas payload, serta mengembalikan respons JSON terstruktur (`SUCCESS` / `FAILED`) seraya menyimpan payload dan status transaksi ke `sap.sync.log`.

## Capabilities
### New Capabilities
- `master-data-api-connector`: Penyediaan antarmuka REST API JSON `/api/sap/master` untuk menerima dan memproses sinkronisasi data master (Material, Rekanan Bisnis, dan Plant/Lokasi) dari sistem SAP Upper Line secara terotentikasi, idempoten, dan teraudit.

### Modified Capabilities
- `None`

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/controllers/__init__.py`
  - `addons/wms_sap_connector/controllers/main.py`
- **Files to Modify:**
  - `addons/wms_sap_connector/__init__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 2.2.1, 3.2, 3.5.1)
  - `docs/roadmap.md` (Fase 2, Kapabilitas 2.2)
- **Estimated Effort:** 4 jam.
- **Complexity & Risk Analysis:** Risiko tingkat menengah (Medium). Risiko payload invalid, ukuran Base64 gambar besar yang membebani memori, atau token tidak valid dimitigasi dengan blok validasi ketat, sanitasi Base64, dan isolasi penanganan eksepsi dengan pencatatan status `failed` pada `sap.sync.log`.

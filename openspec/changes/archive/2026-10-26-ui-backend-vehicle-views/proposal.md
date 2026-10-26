# Proposal: UI Backend Vehicle Views

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | ui-backend-vehicle-views                      |
| **Roadmap Phase**  | Fase 4: Alur Pengantaran, Armada & Bukti Serah Terima (Outbound & Delivery) |
| **Target Cap.**    | `fleet-management-models`                     |
| **Est. Effort**    | 2 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Meskipun model data backend `wms.vehicle` telah berhasil dibuat dan tervalidasi pada basis data, staf logistik (*Logistics Dispatcher* dan *Warehouse Manager*) saat ini belum memiliki antarmuka grafis visual untuk mengelola, memantau ketersediaan, serta menugaskan supir pada armada kendaraan kargo. Penyediaan antarmuka pengguna standar Odoo 17 (Tree view, Form view, Search view, dan Menu Navigasi Logistik) sangat penting agar pengelolaan armada logistik dapat dilakukan secara efisien, transparan, dan terstruktur sebelum dokumen pengiriman barang keluar (*Outbound Delivery*) dialokasikan ke armada terkait.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 4 (Kapabilitas 4.1).

## What Changes
Perubahan berfokus pada penyusunan antarmuka grafis pengguna (UI/XML) pada backend Odoo 17 untuk entitas `wms.vehicle`:
- **Backend (ORM & Models):**
  - Menggunakan model data backend `wms.vehicle` yang telah tersedia tanpa perubahan skema tabel basis data.
- **Security & Access Rights:**
  - Memastikan seluruh tampilan, window action, dan menu navigasi armada terikat dengan benar pada peran pengguna yang berwenang (`group_wms_dispatcher`, `group_wms_manager`, dan `group_wms_operator`).
- **Views & UI:**
  - Membuat file antarmuka baru `addons/wms_sap_connector/views/wms_vehicle_views.xml`.
  - Mendefinisikan **Tree View** (`view_wms_vehicle_tree`) untuk menampilkan daftar armada kendaraan secara ringkas dengan kolom nomor plat, supir penanggung jawab, kapasitas berat (kg), kapasitas volume (m³), dan badge status operasional berwarna.
  - Mendefinisikan **Form View** (`view_wms_vehicle_form`) lengkap dengan widget statusbar interaktif (`available`, `on_delivery`, `maintenance`), input nomor plat kendaraan yang jelas, serta pengelompokan rapi antara data pengemudi dan kapasitas angkut muatan.
  - Mendefinisikan **Search View** (`view_wms_vehicle_search`) dengan fitur pencarian teks nomor plat dan supir, filter cepat status operasional (*Tersedia*, *Dalam Pengantaran*, *Perawatan*), serta pengelompokan (*group by*) berdasarkan status dan supir.
  - Mendefinisikan **Window Action** (`action_wms_vehicle`) untuk membuka antarmuka manajemen armada kendaraan.
  - Mendefinisikan struktur **Menu Navigasi**: Menu utama "Logistics & Delivery" (`menu_wms_logistics_root`) di bawah `stock.menu_stock_root` dan submenu "Fleet Vehicles" (`menu_wms_vehicle`).
  - Mendaftarkan file XML views ke dalam daftar data manifest `addons/wms_sap_connector/__manifest__.py`.
- **Integration & API:**
  - Tidak ada perubahan endpoint API pada change ini.

## Capabilities
### New Capabilities
- `None`

### Modified Capabilities
- `fleet-management-models`: Penyediaan antarmuka grafis Odoo (Tree view, Form view, Search view, Window Action, dan Menu Navigasi Logistik) untuk visualisasi dan manajemen data armada kendaraan kargo (wms.vehicle).

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/views/wms_vehicle_views.xml`
  - `addons/wms_sap_connector/tests/test_vehicle_views.py`
- **Files to Modify:**
  - `addons/wms_sap_connector/__manifest__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 3.2, 3.6)
  - `docs/roadmap.md` (Fase 4, Kapabilitas 4.1)
- **Estimated Effort:** 2 jam.
- **Complexity & Risk Analysis:** Kompleksitas dan risiko rendah (Low Risk) karena hanya menambahkan definisi views dan menu XML deklaratif Odoo 17 tanpa mutasi skema ORM basis data.

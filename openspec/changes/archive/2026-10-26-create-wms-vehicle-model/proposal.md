# Proposal: Create WMS Vehicle Model

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | create-wms-vehicle-model                      |
| **Roadmap Phase**  | Fase 4: Alur Pengantaran, Armada & Bukti Serah Terima (Outbound & Delivery) |
| **Target Cap.**    | `fleet-management-models`                     |
| **Est. Effort**    | 2 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Dalam operasional sistem pergudangan dan logistik Two-Tier WMS terintegrasi SAP, pengiriman pesanan keluar (Outbound Delivery) memerlukan pencatatan dan pengelolaan armada transportasi kargo secara terstruktur. Saat ini sistem belum memiliki entitas khusus untuk mencatat data armada kendaraan logistik beserta kapasitas angkut fisik (berat dan volume kubikasi) serta supir yang bertanggung jawab. Penyediaan model data armada kendaraan `wms.vehicle` menjadi landasan fundamental (*backend foundation*) sebelum tahapan penugasan armada (*dispatching*), penghitungan utilisasi muatan kendaraan (*load capacity*), penerbitan Surat Jalan resmi, hingga pencatatan bukti serah terima digital (*Proof of Delivery / POD*).
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 4 (Kapabilitas 4.1).

## What Changes
Perubahan berfokus pada penyediaan entitas model ORM backend untuk pengelolaan armada kendaraan logistik beserta kontrol keamanan hak akses:
- **Backend (ORM & Models):**
  - Membuat model data baru `wms.vehicle` dengan atribut utama: `license_plate` (Char, Wajib, Unik, `_rec_name`), `driver_id` (Many2one ke `res.partner`), `max_weight` (Float, kapasitas muatan berat kargo dalam kg), `max_volume` (Float, kapasitas volume kubikasi kargo dalam m³), dan `state` (Selection: `available`, `on_delivery`, `maintenance`, default: `available`).
  - Menambahkan konstrain SQL integritas data untuk memastikan nomor plat polisi kendaraan (`license_plate`) unik pada database.
  - Menambahkan validasi ORM (`@api.constrains`) untuk memastikan kapasitas berat (`max_weight`) dan volume (`max_volume`) bernilai non-negatif (>= 0).
  - Mendefinisikan konstanta status kendaraan pada `constants.py`.
- **Security & Access Rights:**
  - Mendaftarkan hak akses model `wms.vehicle` pada `ir.model.access.csv`:
    - `Logistics Dispatcher` (`group_wms_dispatcher`): Akses penuh (CRUD).
    - `Warehouse Manager` (`group_wms_manager`): Akses penuh (CRUD).
    - `Warehouse Operator` (`group_wms_operator`): Hak baca (*read-only*).
    - `System Administrator` (`base.group_system`): Akses penuh (CRUD).
- **Views & UI:**
  - Tidak ada perubahan file XML view pada change ini. Antarmuka formulir, tabel (*tree view*), dan menu navigasi armada logistik akan diimplementasikan secara terpisah pada change berikutnya `ui-backend-vehicle-views` sesuai roadmap.
- **Integration & API:**
  - Mempersiapkan relasi model `wms.vehicle` agar dapat direferensikan oleh dokumen pengiriman `stock.picking` (`vehicle_id`) pada kapabilitas `outbound-dispatch-surat-jalan`.

## Capabilities
### New Capabilities
- `fleet-management-models`: Penyediaan entitas model pengelolaan armada kendaraan kargo (wms.vehicle) beserta kapasitas muatan berat dan volume kubikasi, penugasan supir, dan status operasional armada.

### Modified Capabilities
- `None`

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/models/wms_vehicle.py`
  - `addons/wms_sap_connector/tests/test_wms_vehicle.py`
- **Files to Modify:**
  - `addons/wms_sap_connector/constants.py`
  - `addons/wms_sap_connector/models/__init__.py`
  - `addons/wms_sap_connector/security/ir.model.access.csv`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 3.2, 3.6)
  - `docs/roadmap.md` (Fase 4, Kapabilitas 4.1)
- **Estimated Effort:** 2 jam.
- **Complexity & Risk Analysis:** Kompleksitas dan risiko rendah (Low Risk) karena merupakan penambahan model data baru mandiri tanpa mengubah alur data yang telah berjalan sebelumnya. Mitigasi integritas data ditangani melalui SQL constraint dan ORM check constraints.

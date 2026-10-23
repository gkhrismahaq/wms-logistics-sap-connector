# Proposal: Setup Wms Security Groups

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | setup-wms-security-groups                     |
| **Roadmap Phase**  | Fase 1: Inisialisasi Ekosistem & Modul Inti (Foundation) |
| **Target Cap.**    | `integration-audit-log`                       |
| **Est. Effort**    | 2 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Dalam sistem Two-Tier ERP WMS dan integrasi SAP, pembatasan hak akses berbasis peran (*Role-Based Access Control* / RBAC) sangat krusial untuk menjaga integritas data operasional dan keamanan log sinkronisasi. Tanpa pendefinisian grup keamanan pengguna dan Access Control List (ACL) yang terstruktur, model audit log `sap.sync.log` yang telah dibuat pada modul `wms_sap_connector` berisiko tidak dapat diakses oleh pengguna yang berwenang atau sebaliknya dapat dimodifikasi dan dihapus secara sembarangan oleh peran non-manajerial. Konfigurasi sekuriti ini mendefinisikan tiga peran operasional inti (Warehouse Operator, Logistics Dispatcher, dan Warehouse Manager) serta mengamankan hak akses model `sap.sync.log` sesuai prinsip *least privilege*.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.6 dan [roadmap.md](../../docs/roadmap.md) — Fase 1 (Capability 1.2).

## What Changes
- **Backend (ORM & Models):** Tidak ada pembuatan model data ORM atau field baru. Struktur kelas dan bidang data pada `addons/wms_sap_connector/models/sap_sync_log.py` tetap dipertahankan sesuai spesifikasi fondasi.
- **Security & Access Rights:**
  - Pendefinisian kategori modul keamanan `ir.module.category` (`module_category_wms_logistics`) pada `addons/wms_sap_connector/security/security.xml`.
  - Pendefinisian grup keamanan Odoo (`res.groups`) pada `addons/wms_sap_connector/security/security.xml` untuk tiga peran operasional:
    - `group_wms_operator`: Pengguna Gudang (Warehouse Operator / Staf Gudang) dengan hak terbatas pada pemindaian barcode, dokumen picking, dan alokasi rak.
    - `group_wms_dispatcher`: Staf Logistik (Logistics Dispatcher) dengan hak pengelolaan armada kendaraan, penugasan supir, pencetakan Surat Jalan, dan verifikasi POD.
    - `group_wms_manager`: Manajer Gudang (Warehouse Manager / Kepala Gudang) dengan hak administratif penuh pada operasional gudang serta penanganan log galat pada antarmuka `sap.sync.log`, mewarisi hak akses (`implied_ids`) dari `group_wms_operator` dan `group_wms_dispatcher`.
  - Konfigurasi Access Control List pada `addons/wms_sap_connector/security/ir.model.access.csv` untuk entitas `sap.sync.log` (`model_sap_sync_log`):
    - `group_wms_manager`: Izin penuh CRUD (read=1, write=1, create=1, unlink=1).
    - `group_wms_operator`: Izin baca saja untuk keperluan monitoring dan audit (read=1, write=0, create=0, unlink=0).
    - `group_wms_dispatcher`: Izin baca saja untuk visibilitas status dokumen logistik (read=1, write=0, create=0, unlink=0).
    - Administrator Sistem (`base.group_system`): Izin penuh CRUD (read=1, write=1, create=1, unlink=1).
  - Pendaftaran file sekuriti `security/security.xml` dan `security/ir.model.access.csv` ke dalam daftar `data` pada `addons/wms_sap_connector/__manifest__.py` dengan urutan pemuatan yang benar (`security.xml` terlebih dahulu sebelum `ir.model.access.csv`).
- **Views & UI:** Tidak ada penambahan file view XML baru pada change ini. Antarmuka Tree, Form view, dan menu navigasi log sinkronisasi akan diimplementasikan pada change berikutnya `ui-backend-sync-log-views`.
- **Integration & API:** Memastikan integritas keamanan pada layer data log sinkronisasi sehingga rekaman transaksi integrasi SAP terlindungi dari manipulasi langsung oleh pengguna yang tidak berwenang.

## Capabilities
### New Capabilities
- `None`

### Modified Capabilities
- `integration-audit-log`: Penambahan spesifikasi hak akses peran pengguna (Warehouse Operator, Logistics Dispatcher, dan Warehouse Manager) serta aturan Access Control List (ACL) pada model `sap.sync.log`.

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/security/security.xml`
  - `addons/wms_sap_connector/security/ir.model.access.csv`
- **Files to Modify:**
  - `addons/wms_sap_connector/__manifest__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 3.6)
  - `docs/roadmap.md` (Capability 1.2)
- **Estimated Effort:** 2 jam.
- **Complexity & Risk Analysis:** Kompleksitas rendah hingga menengah. Risiko utama adalah kesalahan dependensi ID XML saat Odoo memuat file data, misalnya jika `ir.model.access.csv` merujuk ke group ID yang belum dimuat karena urutan deklarasi pada manifest salah, atau kesalahan penulisan ID model (`model_sap_sync_log`). Mitigasi dilakukan dengan mendaftarkan `security/security.xml` mendahului `security/ir.model.access.csv` pada manifest `__manifest__.py`, serta memverifikasi kesesuaian penamaan model Odoo 17.

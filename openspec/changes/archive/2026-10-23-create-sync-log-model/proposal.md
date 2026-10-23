# Proposal: Create Sync Log Model

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | create-sync-log-model                         |
| **Roadmap Phase**  | Fase 1: Inisialisasi Ekosistem & Modul Inti (Foundation) |
| **Target Cap.**    | `integration-audit-log`                       |
| **Est. Effort**    | 2 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Sistem WMS Two-Tier membutuhkan pencatatan audit komprehensif atas setiap pertukaran data dua arah antara SAP dan Odoo 17 (seperti master material, master partner, pesanan pembelian, instruksi pengiriman, dan konfirmasi barang). Tanpa model log transaksi yang terstruktur, tim operasional gudang dan integrator sistem tidak memiliki visibilitas atas kegagalan payload, jejak respon akuntansi, maupun mekanisme pemicu pengiriman ulang (*retry*) saat terjadi kegagalan transaksi.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 1 (Capability 1.2).

## What Changes
- **Backend (ORM & Models):** Pembuatan model baru `sap.sync.log` pada `addons/wms_sap_connector/models/sap_sync_log.py` beserta bidang data `name`, `sync_type`, `direction`, `payload`, `status`, `error_message`, `sync_date`, dan penyiapan method `action_retry_sync()` untuk memicu pemrosesan ulang transaksi berstatus `failed`. Pendaftaran package models ke dalam `addons/wms_sap_connector/models/__init__.py` dan `addons/wms_sap_connector/__init__.py`.
- **Security & Access Rights:** `None` (definisi grup otorisasi pengguna dan hak akses model `ir.model.access.csv` akan diatur secara komprehensif pada change berikutnya `setup-wms-security-groups`).
- **Views & UI:** `None` (antarmuka Tree, Form view, filter pencarian, dan action menu akan diimplementasikan pada change berikutnya `ui-backend-sync-log-views`).
- **Integration & API:** Pendefinisian struktur data audit log untuk menampung payload JSON pertukaran data integrasi SAP serta log respons jurnal akuntansi SAP.

## Capabilities
### New Capabilities
- `integration-audit-log`: Penyediaan infrastruktur pencatatan rekaman audit transaksi pertukaran data dua arah antara SAP dan Odoo beserta mekanisme pengiriman ulang transaksi galat.

### Modified Capabilities
- `None`

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/models/__init__.py`
  - `addons/wms_sap_connector/models/sap_sync_log.py`
- **Files to Modify:**
  - `addons/wms_sap_connector/__init__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 3.2, 3.4, 3.5.2)
  - `docs/roadmap.md` (Capability 1.2)
- **Estimated Effort:** 2 jam.
- **Complexity & Risk Analysis:** Kompleksitas rendah. Risiko utama adalah ketidaksesuaian nilai pada opsi bidang `Selection` atau tipe data payload terhadap format JSON kontrak integrasi. Mitigasi dilakukan dengan mengadopsi secara ketat spesifikasi teknis dari `docs/tsd.md` Bagian 3.2.

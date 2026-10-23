# Proposal: Ui Backend Sync Log Views

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | ui-backend-sync-log-views                     |
| **Roadmap Phase**  | Fase 1: Inisialisasi Ekosistem & Modul Inti (Foundation) |
| **Target Cap.**    | `integration-audit-log`                       |
| **Est. Effort**    | 2 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Meskipun model data `sap.sync.log` dan aturan keamanan pengguna telah terpasang pada modul `wms_sap_connector`, saat ini belum ada antarmuka pengguna grafis di backend Odoo untuk memvisualisasikan, mencari, menyaring, maupun menindaklanjuti rekaman log integrasi SAP. Tanpa tampilan Tree, Form, Search view, dan menu navigasi terintegrasi, Kepala Gudang (*Warehouse Manager*) dan operator tidak dapat memantau riwayat pertukaran data dua arah, mengidentifikasi pesan galat sinkronisasi, atau mengeksekusi aksi perbaikan tombol "Retry Sync" secara langsung melalui antarmuka web Odoo.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 1 (Capability 1.2).

## What Changes
- **Backend (ORM & Models):** Tidak ada perubahan pada skema model ORM Python. Seluruh field dan method `action_retry_sync()` pada `addons/wms_sap_connector/models/sap_sync_log.py` dimanfaatkan langsung oleh layer tampilan antarmuka.
- **Security & Access Rights:** Tidak ada penambahan grup keamanan baru. Hak akses menu dan view secara otomatis diatur oleh ACL dan grup keamanan yang telah diinisialisasi pada `security/ir.model.access.csv` dan `security/security.xml`.
- **Views & UI:**
  - Pembuatan file view XML `addons/wms_sap_connector/views/sap_sync_log_views.xml`.
  - Definisi List/Tree view (`view_sap_sync_log_tree`) dengan indikator dekorasi warna status Odoo (`decoration-danger="status == 'failed'"`, `decoration-success="status == 'success'"`, `decoration-warning="status == 'pending'"`), menampilkan ringkasan data transaksi (`sync_date`, `name`, `sync_type`, `direction`, `status`, `error_message`).
  - Definisi Form view (`view_sap_sync_log_form`) lengkap dengan widget statusbar, tombol aksi "Retry Sync" (`action_retry_sync`) yang hanya muncul saat record berstatus gagal (`invisible="status != 'failed'"`), pengelompokan informasi header transaksi, serta tab notebook untuk menampilkan payload JSON dan pesan galat teknis secara terstruktur.
  - Definisi Search view (`view_sap_sync_log_search`) dengan filter cepat (status Failed, Pending, Success; arah Inbound, Outbound) dan pengelompokan (*Group By*) berdasarkan Status, Tipe Sinkronisasi, Arah, dan Tanggal Transaksi.
  - Pendaftaran Action Window Odoo (`action_sap_sync_log`) untuk model `sap.sync.log`.
  - Penyematan item menu navigasi "SAP Integration Logs" di bawah aplikasi Inventory (`stock.menu_stock_root`).
  - Pendaftaran file XML views pada atribut `data` di `addons/wms_sap_connector/__manifest__.py`.
- **Integration & API:** Menyediakan visibilitas menyeluruh dan kemampuan penanganan insiden operasional atas payload data integrasi SAP dari sisi front-end Odoo.

## Capabilities
### New Capabilities
- `None`

### Modified Capabilities
- `integration-audit-log`: Penambahan antarmuka visual backend (Tree View, Form View dengan tombol Retry Sync, Search View) dan menu navigasi terpadu untuk model audit log `sap.sync.log`.

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/views/sap_sync_log_views.xml`
- **Files to Modify:**
  - `addons/wms_sap_connector/__manifest__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 3.2, 3.6)
  - `docs/roadmap.md` (Capability 1.2)
- **Estimated Effort:** 2 jam.
- **Complexity & Risk Analysis:** Kompleksitas rendah. Risiko utama adalah kesalahan sintaks pada XML view Odoo 17 (seperti penggunaan sintaks usang `attrs` alih-alih ekspresi langsung `invisible="status != 'failed'"`). Mitigasi dilakukan dengan menerapkan konvensi Odoo 17 modern dan memverifikasi modul menggunakan perintah `make addon wms_sap_connector`.

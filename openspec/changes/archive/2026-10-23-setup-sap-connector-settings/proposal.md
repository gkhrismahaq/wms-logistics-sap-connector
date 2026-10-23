# Proposal: Setup Sap Connector Settings

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | setup-sap-connector-settings                  |
| **Roadmap Phase**  | Fase 1: Inisialisasi Ekosistem & Modul Inti (Foundation) |
| **Target Cap.**    | `sap-connector-settings`                      |
| **Est. Effort**    | 2 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Komunikasi integrasi dua arah antara Odoo 17 WMS dan SAP (seperti pengiriman webhook konfirmasi Goods Issue / GI dan sinkronisasi status) membutuhkan parameter konfigurasi endpoint host dan token otentikasi yang fleksibel serta aman. Saat ini, nilai URL dan token rahasia belum memiliki tempat penyimpanan terpusat pada sistem Odoo, sehingga berisiko di-hardcode ke dalam kode sumber atau menyulitkan peralihan lingkungan (seperti dari server simulator FastAPI lokal ke server staging/production SAP). Perluasan model `res.config.settings` menyediakan antarmuka konfigurasi terpusat pada menu Settings Inventory untuk mengelola kredensial koneksi SAP secara aman dan dinamis.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 1 (Capability 1.3).

## What Changes
- **Backend (ORM & Models):** Pembuatan kelas model `ResConfigSettings` yang mewarisi model `res.config.settings` pada `addons/wms_sap_connector/models/res_config_settings.py` dengan dua bidang konfigurasi: `sap_base_url` (`config_parameter='wms_sap_connector.sap_base_url'`) dan `sap_api_token` (`config_parameter='wms_sap_connector.sap_api_token'`). Pendaftaran modul Python baru pada `addons/wms_sap_connector/models/__init__.py`.
- **Security & Access Rights:** Mengandalkan hak akses bawaan Odoo untuk `res.config.settings` yang secara ketat membatasi modifikasi parameter sistem hanya untuk administrator gudang (`stock.group_stock_manager`) dan superuser sistem (`base.group_system`).
- **Views & UI:** Pembuatan file view XML `addons/wms_sap_connector/views/res_config_settings_views.xml` yang mewarisi view `stock.res_config_settings_view_form` guna menyematkan blok pengaturan "SAP Integration Connector" dengan input `sap_base_url` dan `sap_api_token` (dengan masking password) pada halaman Settings Inventory. Mendaftarkan file XML view pada manifest `addons/wms_sap_connector/__manifest__.py`.
- **Integration & API:** Menyediakan mekanisme penyimpanan konfigurasi persisten terpusat pada tabel `ir.config_parameter` untuk digunakan oleh seluruh controller dan service integrasi konektor SAP ke depannya.

## Capabilities
### New Capabilities
- `sap-connector-settings`: Penyediaan antarmuka konfigurasi terpusat pada menu Settings Odoo untuk menyimpan endpoint host dan token otorisasi SAP.

### Modified Capabilities
- `None`

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/models/res_config_settings.py`
  - `addons/wms_sap_connector/views/res_config_settings_views.xml`
- **Files to Modify:**
  - `addons/wms_sap_connector/models/__init__.py`
  - `addons/wms_sap_connector/__manifest__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 3.2)
  - `docs/roadmap.md` (Capability 1.3)
- **Estimated Effort:** 2 jam.
- **Complexity & Risk Analysis:** Kompleksitas rendah. Risiko utama adalah kesalahan sintaks XPath saat melakukan inheritance pada `stock.res_config_settings_view_form`. Mitigasi dilakukan dengan menargetkan elemen `<app name="stock">` secara presisi sesuai struktur XML view Odoo 17 dan memverifikasinya melalui upgrade modul via `make addon wms_sap_connector`.

# Proposal: Extend Partner Customer Vendor

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | extend-partner-customer-vendor                |
| **Roadmap Phase**  | Fase 2: Perluasan Master Data & Sinkronisasi (Master Data) |
| **Target Cap.**    | `master-data-models`                          |
| **Est. Effort**    | 3 Hours                                       |
| **Risk Level**     | Low                                           |

## Why
Dalam pertukaran data dua arah arsitektur Two-Tier ERP, sistem SAP mengelola data master rekanan bisnis (Vendor/Pemasok dan Customer/Pelanggan) dengan penomoran unik (contoh: `VEND-INDOMARCO`, `CUST-ALFAMART-01`). Dokumen Purchase Order inbound dari SAP merujuk pada kode Vendor SAP, sedangkan instruksi pengiriman Sales Delivery Order outbound merujuk pada kode Customer SAP. Agar sistem WMS Odoo 17 dapat mengenali dan mencocokkan identitas rekanan bisnis secara presisi tanpa menimbulkan duplikasi kontak, model `res.partner` perlu diperluas dengan field kode identifikasi unik SAP (`sap_partner_code`) yang terindeks dan disajikan pada formulir kontak Odoo.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2 dan [roadmap.md](../../docs/roadmap.md) — Fase 2 (Kapabilitas 2.1).

## What Changes
Perubahan mencakup penambahan atribut kode rekanan SAP pada model mitra, penyajian field pada formulir kontak Odoo, serta konfigurasi indeks basis data:
- **Backend (ORM & Models):** Mewarisi model `res.partner` pada `addons/wms_sap_connector/models/res_partner.py` dengan menambahkan bidang `sap_partner_code` (Char, `index=True`, `copy=False`). Mendaftarkan file model ke dalam file inisialisasi `addons/wms_sap_connector/models/__init__.py`.
- **Security & Access Rights:** Menggunakan aturan hak akses standar Odoo untuk model `res.partner`. Staf operasional gudang (`base.group_user` / `group_wms_operator`) memiliki izin baca untuk verifikasi identitas pengirim dan tujuan pengantaran barang, sementara izin modifikasi dibatasi untuk administrator dan staf berwenang.
- **Views & UI:** Mewarisi tampilan Form Kontak `base.view_partner_form` pada `addons/wms_sap_connector/views/res_partner_views.xml` untuk menyematkan bidang `sap_partner_code` di bawah field `vat` (Tax ID) pada kolom informasi utama rekanan. Mendaftarkan file XML view ke dalam manifest `addons/wms_sap_connector/__manifest__.py`.
- **Integration & API:** Field `sap_partner_code` dikonfigurasi dengan indeks pencarian cepat B-Tree (`index=True`) guna mendukung pencarian berkinerja tinggi saat validasi transaksi inbound PO (`vendor_code`) dan outbound SO (`customer_code`) pada tahap integrasi API.

## Capabilities
### New Capabilities
- `None`

### Modified Capabilities
- `master-data-models`: Penambahan requirement baru `[REQ-MD-02]` untuk perluasan model mitra bisnis (`res.partner`) dengan kode identifikasi unik SAP (`sap_partner_code`).

### Removed Capabilities
- `None`

## Impact & Scope
- **Files to Create:**
  - `addons/wms_sap_connector/models/res_partner.py`
  - `addons/wms_sap_connector/views/res_partner_views.xml`
- **Files to Modify:**
  - `addons/wms_sap_connector/models/__init__.py`
  - `addons/wms_sap_connector/__manifest__.py`
- **SSOT Documents Referenced:**
  - `docs/tsd.md` (Bagian 3.2)
  - `docs/roadmap.md` (Kapabilitas 2.1)
- **Estimated Effort:** 3 jam.
- **Complexity & Risk Analysis:** Kompleksitas dan risiko rendah (Low). Implementasi murni menggunakan mekanisme pewarisan ORM (`_inherit = 'res.partner'`) tanpa merusak relasi model mitra bawaan Odoo. Parameter `copy=False` menjamin keunikan identitas rekanan saat kontak diduplikasi.

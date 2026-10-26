# Design Document: Report Official Surat Jalan

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | `report-official-surat-jalan`                 |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `stock.picking`, `stock.move`, `wms.vehicle`  |

## Context
Pada alur logistik pergudangan DC Lowokwaru, kargo pesanan penjualan yang telah selesai melalui proses picking dan packing harus dimuat ke armada pengiriman bersama dokumen fisik legal Surat Jalan (*Delivery Slip*). Surat Jalan ini berfungsi sebagai manifes muatan resmi di perjalanan serta media pembubuhan tanda tangan serah terima fisik (Petugas Gudang, Supir Pengantar, dan Penerima Toko).

Change sebelumnya (`extend-picking-dispatch-fields`) telah melengkapi model `stock.picking` dengan field relasi armada (`vehicle_id`), supir (`driver_id`), serta akumulasi berat (`total_weight`) dan volume (`total_volume`). Change ini berfokus pada perancangan arsitektur QWeb reporting PDF resmi di Odoo 17 untuk menerbitkan dokumen Surat Jalan yang terintegrasi dengan data tersebut.
> **Reference:** [proposal.md](proposal.md) — Why

## Goals / Non-Goals
### Goals
- Menyediakan template laporan QWeb PDF terstandarisasi (`wms_sap_connector.report_surat_jalan`) yang sesuai dengan format resmi Surat Jalan distribusi logistik.
- Menghasilkan barcode Code128 terbaca scanner untuk nomor dokumen transfer Odoo (`picking.name`) dan nomor referensi pesanan SAP (`sap_doc_number`).
- Menyajikan ringkasan spesifikasi armada kendaraan, identitas supir pengantar, serta total muatan kargo (berat kg dan volume m³).
- Menyediakan tabel rincian kargo produk (kode material SAP/SKU, nama produk, kuantitas, UoM) dan 3 kolom pengesahan tanda tangan fisik.
- Mengintegrasikan aksi cetak laporan pada dropdown menu "Print" dan tombol cepat "Print Surat Jalan" pada header form view `stock.picking`.

### Non-Goals
- Implementasi penangkapan tanda tangan digital touch-screen pada web/mobile (merupakan lingkup Proof of Delivery digital di Fase 4.3).
- Modifikasi skema basis data atau penambahan field baru pada tabel `stock.picking` (skema data sudah lengkap).
- Pembuatan parser Python custom `report.stock.picking.custom` (cukup memanfaatkan QWeb template bawaan Odoo 17 yang efisien).

## Decisions (ADR)
### 1. Pemanfaatan Engine QWeb PDF Native Odoo 17 dan Endpoint Barcode Terintegrasi
- **Rationale:** Odoo 17 menyediakan engine pelaporan QWeb PDF yang matang berbasis `wkhtmltopdf` serta generator barcode native via URL controller `/report/barcode/?barcode_type=Code128&value=...`. Pendekatan ini tidak memerlukan dependensi pustaka Python tambahan dan terintegrasi langsung dengan context rendering multi-company Odoo.
- **Alternatives Considered:** Menggunakan pustaka pihak ketiga seperti `reportlab` canvas kustom atau image generator eksternal (meningkatkan kompleksitas kode dan overhead dependensi OS).
- **Consequences:** Layout laporan harus dirancang rapi dengan CSS teruji agar kompatibel penuh dengan rendering `wkhtmltopdf` versi 0.12.5+.

### 2. Pola Arsitektur Template Modular: Wrapper dan Document Template
- **Rationale:** Mengikuti standar Clean Architecture Odoo 17, laporan dipecah menjadi dua bagian:
  1. `<template id="report_surat_jalan">`: Berfungsi sebagai iterasi loop atas recordset (`t-foreach="docs" t-as="o"`) dengan pengaturan bahasa partner (`t-lang="o.partner_id.lang"`).
  2. `<template id="report_surat_jalan_document">`: Berfungsi sebagai pembangun dokumen spesifik yang dibungkus oleh layout standar `web.external_layout`.
- **Alternatives Considered:** Template monolitik tunggal tanpa pemisahan dokumen (menyulitkan inheritance downstream dan duplikasi logika multi-record).
- **Consequences:** Struktur XML lebih bersih, modular, dan mempermudah unit testing report rendering.

### 3. Integrasi Aksi Cetak: Report Binding dan Tombol Cepat pada Header Form
- **Rationale:** Menetapkan atribut `binding_model_id="stock.model_stock_picking"` dan `binding_type="report"` pada record `ir.actions.report` agar laporan otomatis terdaftar pada menu Print standar Odoo. Selain itu, tombol cepat `<button name="%(action_report_surat_jalan)d" string="Print Surat Jalan" type="action" class="btn-primary" invisible="picking_type_code != 'outgoing'"/>` ditambahkan pada header form view `stock.view_picking_form` untuk efisiensi operasional petugas gudang.
- **Alternatives Considered:** Hanya mengandalkan menu aksi dropdown (membutuhkan klik ekstra oleh staf gudang di lapangan).
- **Consequences:** Penyesuaian deklarasi XML pada `views/stock_picking_views.xml`.

## Technical Architecture & Data Schema

### 1. Deklarasi Action Report (`report/report_surat_jalan.xml`)
```xml
<record id="action_report_surat_jalan" model="ir.actions.report">
    <field name="name">Surat Jalan (Delivery Slip)</field>
    <field name="model">stock.picking</field>
    <field name="report_type">qweb-pdf</field>
    <field name="report_name">wms_sap_connector.report_surat_jalan</field>
    <field name="report_file">wms_sap_connector.report_surat_jalan</field>
    <field name="print_report_name">'Surat Jalan - %s' % (object.name)</field>
    <field name="binding_model_id" ref="stock.model_stock_picking"/>
    <field name="binding_type">report</field>
</record>
```

### 2. Struktur Template Dokumen QWeb (`report_surat_jalan_document`)
```xml
<template id="report_surat_jalan_document">
    <t t-call="web.external_layout">
        <t t-set="o" t-value="o.with_context(lang=lang)"/>
        <div class="page">
            <!-- Header & Barcode Section -->
            <!-- Customer & Delivery Destination Info -->
            <!-- Fleet, Driver, Weight, and Volume Summary -->
            <!-- Cargo Items Table -->
            <!-- 3-Column Signature Blocks -->
        </div>
    </t>
</template>
```

### 3. Penempatan Tombol Form Header (`views/stock_picking_views.xml`)
```xml
<xpath expr="//header" position="inside">
    <button name="%(wms_sap_connector.action_report_surat_jalan)d"
            string="Print Surat Jalan"
            type="action"
            class="btn-primary"
            invisible="picking_type_code != 'outgoing'"/>
</xpath>
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Terjadi error rendering jika field armada atau supir bernilai kosong (`False`) | Low | Gunakan fallback ekspresi ternary pada template QWeb: `<span t-esc="o.vehicle_id.license_plate or '-'"/>` dan `<span t-esc="o.driver_id.name or '-'"/>`. |
| Format barcode tidak terbaca pada wkhtmltopdf akibat kegagalan resolusi URL lokal | Medium | Gunakan path native Odoo barcode widget atau endpoint standar controller Odoo `/report/barcode/?barcode_type=Code128&amp;value=...` yang dieksekusi secara efisien oleh base web module. |
| Pergeseran posisi 3 kolom tanda tangan pada halaman cetak kertas A4 | Low | Terapkan grid layout CSS bootstrap standar Odoo (`row` dan `col-4`) dengan border dan text alignment yang terdefinisi eksplisit. |

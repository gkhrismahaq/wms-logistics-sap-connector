# Design Document: Feature Driver Proof of Delivery

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | `feature-driver-proof-of-delivery`            |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `stock.picking`                               |

## Context
Pada alur pemenuhan pesanan penjualan dan distribusi logistik DC Lowokwaru, kargo yang telah dikirim menggunakan armada kendaraan dan supir penanggung jawab harus diserahkan kepada pihak penerima di lokasi tujuan. Sesuai spesifikasi SSOT pada `docs/tsd.md`, tahap akhir penyerahan barang di lapangan wajib didokumentasikan dengan bukti serah terima digital (*Proof of Delivery / POD*).

Model `stock.picking` saat ini telah memiliki informasi nomor referensi SAP (`sap_doc_number`), status sinkronisasi (`sap_sync_status`), penugasan armada (`vehicle_id`), supir (`driver_id`), serta akumulasi total berat dan volume muatan. Dokumen Surat Jalan resmi pun telah dapat diterbitkan. Change ini mengimplementasikan pencatatan bukti POD (berkas gambar foto/tanda tangan, nama penerima, dan timestamp serah terima) sebagai prasyarat verifikasi sebelum memicu webhook Goods Issue ke SAP Upper Line pada tahapan berikutnya.
> **Reference:** [proposal.md](proposal.md) — Why

## Goals / Non-Goals
### Goals
- Memperluas model `stock.picking` dengan field `proof_of_delivery` (Binary, `attachment=True`), `pod_signed_by` (Char), `pod_timestamp` (Datetime), dan field terkomputasi `has_pod` (Boolean, `store=True`, `index=True`).
- Menerapkan otomatisasi penetapan waktu serah terima (`pod_timestamp`) ke waktu saat ini (`fields.Datetime.now()`) saat berkas foto atau nama penerima diisi tanpa tanggal manual.
- Menyediakan tab antarmuka khusus "Proof of Delivery (POD)" pada form view `stock.view_picking_form` dengan widget pratinjau gambar (`widget="image"`).
- Menyediakan kolom visibilitas POD pada tree view `vpicktree_inherit_sap`.
- Menyediakan filter cepat "Has POD" dan "Missing POD" pada search view `stock.view_picking_internal_search`.

### Non-Goals
- Transmisi webhook notifikasi Goods Issue (GI) ke SAP Upper Line (akan dikerjakan pada change berikutnya `webhook-notify-sap-goods-issue` sesuai roadmap Fase 4.3).
- Modifikasi model kargo atau data pergerakan stok `stock.move`.
- Integrasi GPS geolocation realtime (lingkup pengantaran offline-first mobile yang berada di luar cakupan backend Odoo).

## Decisions (ADR)
### 1. Penyimpanan Berkas Gambar POD melalui Attachment Filestore (`attachment=True`)
- **Rationale:** Mengaktifkan atribut `attachment=True` pada field `fields.Binary` membuat berkas gambar foto atau pindaian tanda tangan disimpan di filestore sistem operasi (`/var/lib/odoo/filestore`), bukan disimpan sebagai bytecode Base64 di baris tabel PostgreSQL `stock_picking`. Pendekatan ini menjaga performa query basis data tetap optimal dan mencegah pembengkakan tabel transfer.
- **Alternatives Considered:** Menyimpan gambar Base64 langsung di database PostgreSQL (memperlambat query dan indeks tabel) atau menggunakan URL penyimpanan S3 pihak ketiga (menambah ketergantungan infrastruktur eksternal).
- **Consequences:** Berkas fisik tersimpan di filestore lokal container yang sudah dipetakan ke volume persisten host Docker.

### 2. Otomatisasi Timestamp POD dan Komputasi Status `has_pod`
- **Rationale:** Di lapangan, staf logistik atau kurir sering kali hanya mengunggah foto penerimaan atau memasukkan nama penerima barang. Dengan mendeteksi perubahan pada field POD melalui method `@api.onchange('proof_of_delivery', 'pod_signed_by')` dan fallback pada `write()`, sistem secara otomatis membubuhkan `pod_timestamp = fields.Datetime.now()`. Selain itu, field boolean `has_pod` dikomputasi dan disimpan di database (`store=True`, `index=True`) untuk mempercepat penyaringan dokumen.
- **Alternatives Considered:** Mengharuskan pengguna memilih tanggal secara manual (menimbulkan friksi operasional dan berisiko salah catat).
- **Consequences:** Fleksibilitas tetap terjaga karena pengguna tetap dapat melakukan koreksi manual jika diperlukan pencatatan susulan.

### 3. Pemisahan Halaman Khusus Form View Berdasarkan Tipe Operasi
- **Rationale:** Halaman tab notebook `"page_proof_of_delivery"` hanya relevan untuk dokumen pengeluaran barang (`picking_type_code == 'outgoing'`). Memberikan atribut visibilitas dinamis `invisible="picking_type_code != 'outgoing'"` menjaga antarmuka tetap bersih dan tidak mengganggu alur penerimaan barang masuk (*Receipts*) maupun transfer internal.
- **Alternatives Considered:** Menggabungkan field POD ke dalam tab general atau tab Fleet (membuat formulir terlihat padat dan kurang terstruktur).
- **Consequences:** Antarmuka formulir transfer lebih modular dan ergonomis bagi staf gudang dan supir pengantar.

## Technical Architecture & Data Schema

### 1. Deklarasi Model Python (`models/stock_picking.py`)
```python
class StockPicking(models.Model):
    _inherit = "stock.picking"

    proof_of_delivery = fields.Binary(
        string="Proof of Delivery (Image / Signature)",
        attachment=True,
        copy=False,
        help="Photo proof of physical handover or scanned signature at destination.",
    )
    pod_signed_by = fields.Char(
        string="Received / Signed By",
        copy=False,
        help="Full name of store receiver or authorized person receiving the cargo.",
    )
    pod_timestamp = fields.Datetime(
        string="POD Timestamp",
        copy=False,
        help="Timestamp when proof of delivery was recorded.",
    )
    has_pod = fields.Boolean(
        string="Has POD",
        compute="_compute_has_pod",
        store=True,
        index=True,
        help="Indicates whether physical proof of delivery is available.",
    )

    @api.depends("proof_of_delivery", "pod_signed_by")
    def _compute_has_pod(self):
        for picking in self:
            picking.has_pod = bool(picking.proof_of_delivery or picking.pod_signed_by)

    @api.onchange("proof_of_delivery", "pod_signed_by")
    def _onchange_pod_fields(self):
        if (self.proof_of_delivery or self.pod_signed_by) and not self.pod_timestamp:
            self.pod_timestamp = fields.Datetime.now()
```

### 2. Struktur XML View Form & Search (`views/stock_picking_views.xml`)
```xml
<!-- Form View Tab Injection -->
<xpath expr="//notebook" position="inside">
    <page string="Proof of Delivery (POD)" name="page_proof_of_delivery"
          invisible="picking_type_code != 'outgoing'">
        <group>
            <group string="Handover Details">
                <field name="pod_signed_by" placeholder="e.g. Budi Santoso (Store Manager)"/>
                <field name="pod_timestamp"/>
                <field name="has_pod"/>
            </group>
            <group string="Visual Proof / Photo">
                <field name="proof_of_delivery" widget="image" class="oe_avatar"
                       options="{'preview_image': 'proof_of_delivery', 'size': [300, 300]}"/>
            </group>
        </group>
    </page>
</xpath>

<!-- Search View Filters -->
<xpath expr="//filter[@name='filter_has_vehicle']" position="after">
    <separator/>
    <filter string="Has POD" name="filter_has_pod" domain="[('has_pod', '=', True)]"/>
    <filter string="Missing POD" name="filter_missing_pod"
            domain="[('picking_type_code', '=', 'outgoing'), ('has_pod', '=', False)]"/>
</xpath>
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Ukuran file gambar yang diunggah staf lapangan terlalu besar | Low | Penerapan `attachment=True` memastikan file disimpan di filestore Odoo, serta rendering UI menggunakan parameter sizing `[300, 300]` untuk efisiensi transfer data web. |
| Pengguna lupa mengisi timestamp serah terima | Low | Method onchange dan pengecekan ORM otomatis mengisi `pod_timestamp` dengan `fields.Datetime.now()` saat gambar atau nama penerima diunggah. |
| Field POD tampil pada dokumen penerimaan barang vendor (Inbound) | Low | Atribut XML `invisible="picking_type_code != 'outgoing'"` memastikan tab POD hanya muncul pada dokumen pengantaran keluar. |

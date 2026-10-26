# Design Document: Extend Picking Dispatch Fields

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | extend-picking-dispatch-fields                |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `stock.picking`, `wms.vehicle`, `res.partner` |

## Context
Pada arsitektur Two-Tier ERP WMS ([tsd.md](../../docs/tsd.md) — Bagian 3.2), instruksi pengiriman penjualan dari SAP Upper Line dikonversi menjadi dokumen Delivery Order (`stock.picking` dengan tipe operasi `outgoing`). Sebelum dokumen Surat Jalan dicetak dan kargo didistribusikan ke pelanggan, staf logistik (Dispatcher) harus menugaskan armada truk fisik (`wms.vehicle`) dan supir pengantar (`res.partner`), serta memastikan bobot dan volume kargo tidak melampaui daya angkut armada.

Saat ini model `stock.picking` telah memiliki nomor dokumen SAP (`sap_doc_number`) dan status sinkronisasi (`sap_sync_status`), namun belum terhubung ke entitas armada logistik dan belum memiliki kalkulasi akumulasi muatan barang. Change ini melengkapi model `stock.picking` dengan field dispatch relasional dan komputasi otomatis sebelum change pelaporan Surat Jalan (`report-official-surat-jalan`) dikerjakan.

## Goals / Non-Goals
### Goals
- Menambahkan relasi Many2one `vehicle_id` (`wms.vehicle`) dan `driver_id` (`res.partner`) pada model `stock.picking`.
- Mengimplementasikan event `@api.onchange('vehicle_id')` untuk mengisi supir default dari `vehicle_id.driver_id` secara otomatis dengan tetap memungkinkan penggantian manual.
- Mengimplementasikan field terkomputasi `total_weight` (Float, kg) dan `total_volume` (Float, m³) dengan penyimpanan basis data (`store=True`) berdasarkan perkalian kuantitas baris `move_ids` dan berat/volume produk.
- Menambahkan validasi kapasitas muatan armada via `@api.constrains('vehicle_id', 'total_weight', 'total_volume')` untuk mencegah kelebihan muatan fisik (*overcapacity*).
- Menampilkan group informasi armada dan pengantaran pada form view `stock.view_picking_form` serta kolom armada pada tree view `vpicktree_inherit_sap`.
- Menyediakan automated unit test lengkap untuk menguji perhitungan akumulasi muatan, event onchange, dan constraint validasi kapasitas.

### Non-Goals
- Tidak mendesain template laporan cetak PDF Surat Jalan (lingkup change `report-official-surat-jalan`).
- Tidak mengimplementasikan field bukti penerimaan digital POD (`proof_of_delivery`, `pod_signed_by`, `pod_timestamp`) dan pengiriman sinyal Goods Issue ke SAP (lingkup change Fase 4.3).

## Decisions (ADR)
### 1. Penyimpanan Nilai Komputasi Muatan (`store=True`) dengan Dependensi Spesifik
- **Rationale:** Petugas logistik dan operator gudang membutuhkan akses cepat untuk melihat total beban muatan armada pada list view dan filter pencarian. Menyimpan field `total_weight` dan `total_volume` pada basis data (`store=True`) dengan dekorator `@api.depends('move_ids.product_uom_qty', 'move_ids.product_id.weight', 'move_ids.product_id.volume', 'move_ids.state')` menjamin kecepatan pembacaan tanpa kalkulasi runtime berulang. Baris move yang berstatus `cancel` dikecualikan dari akumulasi.
- **Alternatives Considered:** Menggunakan compute field murni tanpa `store=True`. Ditolak karena memperlambat waktu rendering Tree view pada volume picking yang besar dan mencegah pengurutan data di database.
- **Consequences:** Sedikit peningkatan write activity saat kuantitas barang diubah, namun sangat menguntungkan performa operasional harian.

### 2. Pola Penugasan Supir Fleksibel Melalui Onchange (Bukan Related Field Murni)
- **Rationale:** Setiap armada `wms.vehicle` umumnya memiliki supir tetap penanggung jawab (`driver_id`). Namun dalam praktik operasional lapangan logistik, pergantian supir bertugas sering terjadi akibat rotasi shift, sakit, atau penugasan darurat. Dengan menggunakan `@api.onchange('vehicle_id')`, sistem mengisi `driver_id` secara otomatis saat armada dipilih, namun Dispatcher tetap memiliki fleksibilitas untuk memilih supir pengganti tanpa harus memodifikasi master data kendaraan.
- **Alternatives Considered:** Menggunakan field `related="vehicle_id.driver_id", readonly=True`. Ditolak keras karena mengunci penugasan supir dan tidak mencerminkan fleksibilitas operasional logistik nyata.
- **Consequences:** Memberikan keseimbangan sempurna antara kenyamanan otomatisasi input dan fleksibilitas penugasan supir lapangan.

### 3. Validasi Batas Kapasitas Armada via Python ORM `@api.constrains`
- **Rationale:** Keamanan transportasi dan regulasi tonase jalan raya mengharuskan muatan kargo tidak melebihi kapasitas maksimum armada. Dengan menerapkan constraint pada level ORM, validasi dipastikan berjalan konsisten baik melalui antarmuka web Odoo, panggilan API, maupun skrip internal. Jika `vehicle_id` memiliki batasan `max_weight > 0` dan `total_weight > vehicle_id.max_weight` (atau `max_volume`), sistem memunculkan `ValidationError` informatif yang menyebutkan selisih kelebihan muatan.
- **Alternatives Considered:** Validasi hanya berupa peringatan dialog onchange di Web Client. Ditolak karena tidak mencegah penyimpanan data jika pengguna mengabaikan peringatan atau saat data disimpan via transaksi backend.
- **Consequences:** Menjamin kepatuhan standar keselamatan armada secara tegas pada tingkat integritas data.

## Technical Architecture & Data Schema

### 1. Struktur Field Model `stock.picking`
```python
class StockPicking(models.Model):
    _inherit = "stock.picking"

    vehicle_id = fields.Many2one(
        comodel_name="wms.vehicle",
        string="Vehicle / Fleet",
        domain="[('state', '!=', 'maintenance')]",
        index=True,
        copy=False,
        help="Physical cargo delivery vehicle assigned to this transfer.",
    )
    driver_id = fields.Many2one(
        comodel_name="res.partner",
        string="Driver",
        domain="[('is_company', '=', False)]",
        copy=False,
        help="Responsible courier or driver conducting the delivery.",
    )
    total_weight = fields.Float(
        string="Total Weight (kg)",
        compute="_compute_total_weight_volume",
        store=True,
        digits="Stock Weight",
        help="Aggregated total weight in kilograms computed from all active stock moves.",
    )
    total_volume = fields.Float(
        string="Total Volume (m³)",
        compute="_compute_total_weight_volume",
        store=True,
        digits=(12, 4),
        help="Aggregated total volume in cubic meters computed from all active stock moves.",
    )

    @api.onchange("vehicle_id")
    def _onchange_vehicle_id(self):
        """Auto-populates driver from assigned vehicle default driver."""
        if self.vehicle_id and self.vehicle_id.driver_id:
            self.driver_id = self.vehicle_id.driver_id

    @api.depends(
        "move_ids.product_uom_qty",
        "move_ids.product_id.weight",
        "move_ids.product_id.volume",
        "move_ids.state",
    )
    def _compute_total_weight_volume(self):
        """Computes accumulated weight and volume of all non-cancelled stock moves."""
        for picking in self:
            weight = 0.0
            volume = 0.0
            for move in picking.move_ids.filtered(lambda m: m.state != "cancel"):
                qty = move.product_uom_qty or 0.0
                prod = move.product_id
                if prod:
                    weight += (prod.weight or 0.0) * qty
                    volume += (prod.volume or 0.0) * qty
            picking.total_weight = weight
            picking.total_volume = volume

    @api.constrains("vehicle_id", "total_weight", "total_volume")
    def _check_vehicle_capacity(self):
        """Enforces vehicle cargo capacity limits against aggregated weight and volume."""
        for picking in self:
            if not picking.vehicle_id:
                continue
            v = picking.vehicle_id
            if v.max_weight > 0.0 and picking.total_weight > v.max_weight:
                raise ValidationError(
                    f"Overcapacity Error: Total weight ({picking.total_weight:.2f} kg) "
                    f"exceeds vehicle maximum weight capacity ({v.max_weight:.2f} kg) "
                    f"for vehicle '{v.license_plate}'."
                )
            if v.max_volume > 0.0 and picking.total_volume > v.max_volume:
                raise ValidationError(
                    f"Overcapacity Error: Total volume ({picking.total_volume:.4f} m³) "
                    f"exceeds vehicle maximum volume capacity ({v.max_volume:.4f} m³) "
                    f"for vehicle '{v.license_plate}'."
                )
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Master produk belum memiliki data `weight` atau `volume`. | Low | Komputasi menangani nilai kosong/nol secara anggun (`prod.weight or 0.0`) tanpa menghasilkan error. |
| Armada kendaraan tidak memiliki batasan kapasitas muatan (`max_weight = 0` atau `max_volume = 0`). | Low | Validasi kapasitas hanya aktif jika nilai kapasitas kendaraan lebih besar dari 0 (`> 0.0`), mendukung kendaraan dengan kapasitas tak terbatas. |
| Pengguna memilih supir yang merupakan badan usaha (`is_company = True`). | Low | Domain filter `[('is_company', '=', False)]` membatasi pilihan hanya pada kontak perorangan. |

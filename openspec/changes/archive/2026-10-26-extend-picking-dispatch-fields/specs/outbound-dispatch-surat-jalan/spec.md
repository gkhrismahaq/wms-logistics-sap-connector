# Specification: Outbound Dispatch Surat Jalan

## ADDED Requirements

### Requirement: [REQ-OUT-04] Penugasan Armada Kendaraan dan Supir Pengantar pada Dokumen Delivery Order (stock.picking)
The system MUST menyediakan atribut relasional penugasan armada kendaraan kargo (`vehicle_id`) dan supir pengantar (`driver_id`) pada dokumen transfer `stock.picking` beserta otomatisasi penetapan supir default.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Spesifikasi atribut dan relasi:
- `vehicle_id` (Many2one -> `wms.vehicle`):
  - Label: `"Vehicle / Fleet"`
  - Domain penyaringan: hanya menampilkan armada yang tidak sedang dalam perawatan/bengkel (`[('state', '!=', 'maintenance')]`).
  - Terindeks (`index=True`) dan tidak disalin saat duplikasi dokumen (`copy=False`).
- `driver_id` (Many2one -> `res.partner`):
  - Label: `"Driver"`
  - Domain penyaringan: hanya menampilkan entitas kontak perorangan (`[('is_company', '=', False)]`).
  - Tidak disalin saat duplikasi dokumen (`copy=False`).
- Otomatisasi Onchange (`@api.onchange('vehicle_id')`):
  - Saat pengguna memilih `vehicle_id` pada form `stock.picking`, jika armada tersebut memiliki data supir penanggung jawab (`vehicle_id.driver_id`), sistem secara otomatis mengisi nilai field `driver_id`.
  - Dispatcher tetap diperkenankan mengganti `driver_id` secara manual apabila terjadi pergantian supir bertugas (*shift/substitute*).

#### Scenario: Penugasan Armada Kendaraan dan Otomatisasi Supir Bertugas (Happy Path)
- **GIVEN** dokumen Delivery Order (`stock.picking` bertipe `outgoing`) dan armada kendaraan `B 1234 WMS` yang telah memiliki supir tetap `Budi Santoso`
- **WHEN** staf logistik memilih armada `B 1234 WMS` pada formulir pengantaran
- **THEN** sistem secara otomatis mengisi nilai field `driver_id` dengan `Budi Santoso` dan menyimpan relasi tersebut saat formulir disimpan

#### Scenario: Penggantian Supir Pengantar Secara Manual oleh Dispatcher (Happy Path)
- **GIVEN** dokumen Delivery Order dengan armada `B 1234 WMS` dan supir terisi otomatis `Budi Santoso`
- **WHEN** staf logistik mengubah supir pengantar menjadi supir pengganti `Ahmad Hidayat`
- **THEN** sistem menerima pembaruan tersebut dan menyimpan `driver_id = Ahmad Hidayat` tanpa mengubah supir tetap pada master `wms.vehicle`

### Requirement: [REQ-OUT-05] Komputasi Otomatis Total Berat dan Volume Muatan serta Validasi Kapasitas Armada
The system MUST menghitung akumulasi total berat (`total_weight`) dan total volume kubikasi kargo (`total_volume`) secara otomatis dari seluruh baris pergerakan stok (`move_ids`), serta memvalidasi kesesuaian kapasitas muatan terhadap armada kendaraan yang ditugaskan.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Spesifikasi kalkulasi dan atribut terkomputasi:
- `total_weight` (Float, Read-only):
  - Label: `"Total Weight (kg)"`
  - Formula: $\sum (\text{move.product\_uom\_qty} \times \text{move.product\_id.weight})$ untuk seluruh `move_ids` yang tidak berstatus dibatalkan (`cancel`).
  - Bergantung pada `@api.depends('move_ids.product_uom_qty', 'move_ids.product_id.weight', 'move_ids.state')` dan tersimpan di database (`store=True`).
- `total_volume` (Float, Read-only):
  - Label: `"Total Volume (m³)"`
  - Formula: $\sum (\text{move.product\_uom\_qty} \times \text{move.product\_id.volume})$ untuk seluruh `move_ids` yang tidak berstatus dibatalkan (`cancel`).
  - Bergantung pada `@api.depends('move_ids.product_uom_qty', 'move_ids.product_id.volume', 'move_ids.state')` dan tersimpan di database (`store=True`).
- Validasi Batasan Kapasitas Muatan (*Capacity Validation Constraint*):
  - Method validasi `@api.constrains('vehicle_id', 'total_weight', 'total_volume')`.
  - Jika `vehicle_id` ditetapkan dan `vehicle_id.max_weight > 0` serta `total_weight > vehicle_id.max_weight`:
    - Sistem memicu `ValidationError` yang menyatakan bahwa muatan kargo melebihi batas berat maksimum kendaraan.
  - Jika `vehicle_id` ditetapkan dan `vehicle_id.max_volume > 0` serta `total_volume > vehicle_id.max_volume`:
    - Sistem memicu `ValidationError` yang menyatakan bahwa muatan kargo melebihi batas volume kubikasi maksimum kendaraan.

#### Scenario: Komputasi Akumulasi Total Berat dan Volume Muatan (Happy Path)
- **GIVEN** dokumen Delivery Order dengan 2 baris kargo:
  - 10 unit Kopi (berat 0.5 kg/unit, volume 0.002 m³/unit)
  - 20 unit Teh (berat 0.25 kg/unit, volume 0.001 m³/unit)
- **WHEN** baris barang disimpan pada dokumen transfer
- **THEN** sistem secara otomatis menghitung `total_weight = 10.0 kg` dan `total_volume = 0.04 m³`

#### Scenario: Penolakan Validasi Dokumen Saat Muatan Melebihi Kapasitas Kendaraan (Edge Case)
- **GIVEN** dokumen Delivery Order dengan akumulasi `total_weight = 3000.0 kg`
- **WHEN** pengguna mencoba menetapkan armada kendaraan dengan `max_weight = 2000.0 kg` dan menyimpan dokumen
- **THEN** sistem menolak penyimpanan dan memunculkan `ValidationError` yang menerangkan bahwa muatan melebihi kapasitas maksimum armada

## MODIFIED Requirements
None

## REMOVED Requirements
None

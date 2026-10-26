# Specification: Fleet Management Models

## ADDED Requirements

### Requirement: [REQ-FLT-03] Antarmuka Pengguna Visual dan Menu Navigasi Armada Kendaraan (wms.vehicle Views)
The system MUST menyediakan antarmuka pengguna grafis yang mencakup Tree view, Form view, Search view, Window action, dan struktur Menu navigasi untuk model `wms.vehicle`.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2, 3.6

Spesifikasi antarmuka visual:
- **Tree View (`view_wms_vehicle_tree`):**
  - Kolom data: `license_plate`, `driver_id`, `max_weight`, `max_volume`, dan `state`.
  - Field `state` ditampilkan menggunakan widget badge status berwarna: hijau (`decoration-success`) untuk `available`, biru/info (`decoration-info`) untuk `on_delivery`, dan oranye/warning (`decoration-warning`) untuk `maintenance`.
- **Form View (`view_wms_vehicle_form`):**
  - Header: Bar status interaktif (`widget="statusbar"` dengan `statusbar_visible="available,on_delivery,maintenance"`).
  - Sheet: Field `license_plate` ditampilkan menonjol pada judul utama (`h1`), serta pengelompokan 2 kolom terstruktur untuk penugasan supir (`driver_id`) dan kapasitas muatan kargo (`max_weight` kg dan `max_volume` m³).
- **Search View (`view_wms_vehicle_search`):**
  - Filter pencarian teks bebas pada `license_plate` dan `driver_id`.
  - Filter cepat status operasional armada:
    - "Available / Siap Jalan" (`domain="[('state', '=', 'available')]"`).
    - "On Delivery / Sedang Bertugas" (`domain="[('state', '=', 'on_delivery')]"`).
    - "Maintenance / Perawatan" (`domain="[('state', '=', 'maintenance')]"`).
  - Opsi pengelompokan (*Group By*): berdasarkan status (`state`) dan supir (`driver_id`).
- **Window Action (`action_wms_vehicle`):**
  - Action standar `ir.actions.act_window` untuk memuat tampilan model `wms.vehicle` dengan view mode `tree,form`.
- **Menu Navigasi Logistik:**
  - Menu Induk: "Logistics & Delivery" (`menu_wms_logistics_root`) di bawah menu utama gudang Odoo (`stock.menu_stock_root`) dengan urutan sequence 25.
  - Submenu: "Fleet Vehicles" (`menu_wms_vehicle`) di bawah menu induk logistik yang memicu action `action_wms_vehicle`.

#### Scenario: Visualisasi Daftar Armada dan Form Rinci Kendaraan (Happy Path)
- **GIVEN** data armada kendaraan kargo telah tersimpan dalam basis data
- **WHEN** pengguna membuka menu "Fleet Vehicles" pada antarmuka Odoo
- **THEN** sistem memuat Tree view dengan daftar armada lengkap beserta kapasitas dan badge status, serta membuka Form view yang terstruktur rapi saat salah satu baris dipilih

#### Scenario: Pencarian dan Penyaringan Status Armada (Happy Path)
- **GIVEN** daftar armada kendaraan dengan berbagai status operasional (`available`, `on_delivery`, `maintenance`)
- **WHEN** pengguna menerapkan filter cepat "Available / Siap Jalan" atau melakukan pencarian nomor plat pada Search view
- **THEN** sistem memfilter daftar dan hanya menampilkan armada yang sesuai dengan kriteria filter tersebut

## MODIFIED Requirements
None

## REMOVED Requirements
None

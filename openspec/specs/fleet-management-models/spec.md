# Specification: Fleet Management Models

## Purpose
Menyediakan entitas pengelolaan armada kendaraan kargo dan logistik (*wms.vehicle*) pada Two-Tier WMS Odoo 17 untuk mendukung perencanaan kapasitas muatan, penugasan supir, dan pemantauan status operasional armada pengantaran.

## Requirements

### Requirement: [REQ-FLT-01] Entitas Model Pengelolaan Armada Kendaraan Kargo (wms.vehicle)
The system MUST menyediakan model data `wms.vehicle` untuk mencatat identitas fisik, spesifikasi kapasitas angkut, penugasan supir, dan status operasional armada kendaraan logistik.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.2

Spesifikasi atribut model `wms.vehicle`:
- `license_plate` (Char, Wajib, Unik, `_rec_name`): Nomor plat polisi kendaraan (contoh: 'B 1234 WMS'), terindeks dan wajib unik pada tingkat basis data via SQL constraint.
- `driver_id` (Many2one -> `res.partner`): Mitra penanggung jawab supir armada kargo dengan domain non-perusahaan (`is_company = False`).
- `max_weight` (Float): Kapasitas muatan berat kargo maksimum dalam satuan kilogram (kg), dengan konstrain validasi nilai non-negatif (`max_weight >= 0`).
- `max_volume` (Float): Kapasitas volume kubikasi kargo maksimum dalam satuan meter kubik (m³), dengan konstrain validasi nilai non-negatif (`max_volume >= 0`).
- `state` (Selection: `available`, `on_delivery`, `maintenance`, default: `available`): Status kondisi operasional armada kargo.

#### Scenario: Pembuatan Data Armada Baru dengan Atribut Valid (Happy Path)
- **GIVEN** pengguna memiliki wewenang Logistics Dispatcher atau Warehouse Manager
- **WHEN** membuat record `wms.vehicle` dengan plat nomor unik 'B 1234 WMS', kapasitas muatan berat 2500.0 kg, kapasitas volume 12.5 m³, dan penugasan supir yang valid
- **THEN** sistem berhasil menyimpan record baru dengan status default 'available' dan dapat dijadikan referensi operasional

#### Scenario: Penolakan Duplikasi Nomor Plat Polisi Kendaraan (Edge Case)
- **GIVEN** telah terdapat armada kargo dengan plat nomor 'B 1234 WMS' di dalam sistem
- **WHEN** pengguna mencoba membuat armada baru dengan plat nomor yang sama persis ('B 1234 WMS')
- **THEN** sistem menolak penyimpanan dan memunculkan galat integritas data duplikasi nomor plat polisi (*SQL unique constraint violation*)

#### Scenario: Validasi Nilai Kapasitas Muatan Negatif (Edge Case)
- **GIVEN** formulir input data armada kendaraan kargo
- **WHEN** pengguna memasukkan nilai `max_weight` kurang dari 0 atau `max_volume` kurang dari 0
- **THEN** sistem memicu validasi ORM (`ValidationError`) dan membatalkan proses penyimpanan record

### Requirement: [REQ-FLT-02] Kontrol Hak Akses dan Keamanan Entitas Armada
The system MUST mengonfigurasi kontrol akses data model `wms.vehicle` sesuai matriks peran keamanan Two-Tier WMS.
> **Reference:** [tsd.md](../../docs/tsd.md) — Bagian 3.6

Spesifikasi matriks hak akses pada `ir.model.access.csv`:
- `Logistics Dispatcher` (`group_wms_dispatcher`): Akses penuh (Read: 1, Write: 1, Create: 1, Unlink: 1).
- `Warehouse Manager` (`group_wms_manager`): Akses penuh (Read: 1, Write: 1, Create: 1, Unlink: 1).
- `System Administrator` (`base.group_system`): Akses penuh (Read: 1, Write: 1, Create: 1, Unlink: 1).
- `Warehouse Operator` (`group_wms_operator`): Hak akses hanya-baca (Read: 1, Write: 0, Create: 0, Unlink: 0).

#### Scenario: Akses Penuh bagi Logistics Dispatcher dan Warehouse Manager
- **GIVEN** pengguna terautentikasi dengan peran Logistics Dispatcher atau Warehouse Manager
- **WHEN** melakukan operasi create, read, update, atau delete pada model `wms.vehicle`
- **THEN** sistem mengizinkan seluruh operasi tersebut dieksekusi tanpa kendala pembatasan hak akses

#### Scenario: Pembatasan Akses Modifikasi bagi Warehouse Operator
- **GIVEN** pengguna terautentikasi dengan peran Warehouse Operator
- **WHEN** mencoba membuat (*create*), menyunting (*write*), atau menghapus (*unlink*) data pada model `wms.vehicle`
- **THEN** sistem menolak operasi dengan memicu galat hak akses (*AccessError*) dan hanya mengizinkan pembacaan data (*read-only*)

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

# Design Document: Create WMS Vehicle Model

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | create-wms-vehicle-model                      |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `wms.vehicle`, `res.partner`                  |

## Context
Pada arsitektur Two-Tier WMS dan Logistik yang terintegrasi dengan SAP Upper Line, proses pengiriman barang keluar (*Outbound Delivery*) membutuhkan kesiapan data armada logistik untuk perencanaan penugasan supir (*fleet dispatching*), penghitungan utilisasi kubikasi kargo, dan penerbitan Surat Jalan.

Saat ini modul `wms_sap_connector` telah menyelesaikan kapabilitas penerimaan barang (*Inbound Receipt*, *Putaway*, dan *Goods Receipt Webhook*). Berdasarkan dokumen acuan arsitektur ([tsd.md](../../docs/tsd.md) — Bagian 3.2 & 3.6) dan rencana rilis ([roadmap.md](../../docs/roadmap.md) — Fase 4), langkah pertama pada Fase 4 adalah menyediakan entitas model backend `wms.vehicle` sebagai fondasi utama sebelum antarmuka visual (Tree/Form views) dan relasi ke dokumen transfer `stock.picking` diimplementasikan.

## Goals / Non-Goals
### Goals
- Mendefinisikan model baru `wms.vehicle` dengan field utama: `license_plate`, `driver_id`, `max_weight`, `max_volume`, dan `state`.
- Menetapkan `_rec_name = "license_plate"` agar representasi visual dan relasi Many2one menampilkan nomor plat kendaraan secara natural.
- Menegakkan integritas keunikan nomor plat polisi pada level database melalui `_sql_constraints` (`unique(license_plate)`).
- Menambahkan validasi ORM `@api.constrains` untuk memastikan nilai `max_weight >= 0` dan `max_volume >= 0`.
- Memisahkan definisi konstanta status armada kendaraan ke dalam `constants.py` untuk menjaga konsistensi arsitektur (*Clean Architecture*).
- Mengonfigurasi hak akses keamanan model pada `ir.model.access.csv` untuk peran Dispatcher, Manager, Operator, dan System Administrator.
- Menyediakan automated unit test lengkap untuk verifikasi pembuatan record, constraint duplikasi, validasi kapasitas, dan kontrol hak akses.

### Non-Goals
- Tidak membuat antarmuka pengguna XML (Tree View, Form View, Search View, Action, Menu) pada change ini. Antarmuka pengguna secara khusus akan dikerjakan pada change `ui-backend-vehicle-views`.
- Tidak menambahkan field relasi `vehicle_id` dan `driver_id` ke model `stock.picking` pada change ini (dikerjakan pada change `extend-picking-dispatch-fields`).
- Tidak membuat endpoint REST API eksternal untuk sinkronisasi armada kendaraan.

## Decisions (ADR)
### 1. Penggunaan `_rec_name = "license_plate"` Tanpa Field Tambahan `name`
- **Rationale:** Nomor plat polisi kendaraan (*license plate*) merupakan pengidentifikasi alami (*natural key*) yang paling mudah dikenali oleh personel logistik di lapangan. Dengan menetapkan `_rec_name = "license_plate"`, Odoo ORM secara otomatis menggunakan field ini sebagai label referensi pada widget Many2one, pencarian relasional, dan breadcrumb tanpa memerlukan field `name` terpisah yang redundan.
- **Alternatives Considered:** Menambahkan field `name` terpisah atau membuat *computed field* kombinasi nama dan plat nomor. Alternatif ini ditolak karena menambah redundansi kolom data dan tidak diperlukan pada spesifikasi SSOT Bagian 3.2.
- **Consequences:** Struktur skema model lebih ramping, performa kueri optimal, dan penamaan seragam di seluruh sistem.

### 2. Penegakan Integritas Plat Nomor via SQL Constraint
- **Rationale:** Integritas nomor plat polisi kendaraan wajib dijamin unik di seluruh sistem. Penegakan melalui PostgreSQL Unique Index Constraint (`_sql_constraints`) menjamin integritas pada tingkat *database engine*, kebal terhadap potensi *race condition* konkurensi ketika beberapa pengguna mendaftarkan armada secara simultan.
- **Alternatives Considered:** Menggunakan validasi Python `@api.constrains('license_plate')`. Alternatif ini ditolak karena tidak dapat mencegah konkurensi transaksi multi-koneksi (*concurrency race condition*).
- **Consequences:** Transaksi duplikasi akan langsung ditolak oleh PostgreSQL dan Odoo ORM akan menangani eksepsinya secara aman.

### 3. Validasi Kapasitas Muatan Non-Negatif via `@api.constrains`
- **Rationale:** Secara fisik, kapasitas muatan berat (`max_weight`) dan volume kubikasi (`max_volume`) tidak boleh bernilai negatif. Validasi via ORM `@api.constrains` memungkinkan penyampaian pesan kesalahan bisnis yang informatif dalam Bahasa Indonesia yang ramah pengguna jika terjadi kesalahan input.
- **Alternatives Considered:** Menggunakan SQL check constraint `CHECK (max_weight >= 0)`. Ditolak karena pesan error SQL mentah kurang ramah bagi operator pengguna Odoo.
- **Consequences:** Pengguna mendapatkan umpan balik validasi yang jelas saat memasukkan data yang tidak valid.

### 4. Sentralisasi Konstanta State Kendaraan pada `constants.py`
- **Rationale:** Status armada (`available`, `on_delivery`, `maintenance`) akan digunakan berulang kali di berbagai domain: deklarasi model, logika mutasi status saat pengiriman barang (*dispatching*), filter pencarian, dan penulisan test suite otomatis. Menempatkannya pada `constants.py` mencegah praktik *magic string* dan memastikan *Single Source of Truth* dalam basis kode.
- **Alternatives Considered:** Menuliskan list tuple secara langsung di dalam file `wms_vehicle.py`. Ditolak karena mempersulit pemeliharaan jangka panjang dan melanggar aturan arsitektur proyek.
- **Consequences:** Seluruh referensi status kendaraan terpusat dan mudah diuji.

## Technical Architecture & Data Schema

### 1. Definisi Konstanta Kendaraan (`constants.py`)
```python
VEHICLE_STATE_AVAILABLE = "available"
VEHICLE_STATE_ON_DELIVERY = "on_delivery"
VEHICLE_STATE_MAINTENANCE = "maintenance"

VEHICLE_STATE_SELECTION = [
    (VEHICLE_STATE_AVAILABLE, "Tersedia / Siap Jalan"),
    (VEHICLE_STATE_ON_DELIVERY, "Sedang Bertugas / Pengantaran"),
    (VEHICLE_STATE_MAINTENANCE, "Perawatan / Bengkel"),
]
```

### 2. Struktur Model `wms.vehicle` (`models/wms_vehicle.py`)
```python
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ..constants import (
    VEHICLE_STATE_AVAILABLE,
    VEHICLE_STATE_SELECTION,
)


class WmsVehicle(models.Model):
    _name = "wms.vehicle"
    _description = "WMS Logistics Vehicle"
    _rec_name = "license_plate"
    _order = "license_plate asc"

    license_plate = fields.Char(
        string="License Plate",
        required=True,
        index=True,
        copy=False,
        help="Nomor plat polisi kendaraan armada logistik (contoh: 'B 1234 WMS')",
    )
    driver_id = fields.Many2one(
        "res.partner",
        string="Assigned Driver",
        domain=[("is_company", "=", False)],
        ondelete="set null",
        help="Supir tetap penanggung jawab armada kendaraan",
    )
    max_weight = fields.Float(
        string="Max Weight Capacity (kg)",
        digits=(12, 2),
        default=0.0,
        help="Kapasitas muatan berat maksimum kargo dalam satuan kilogram (kg)",
    )
    max_volume = fields.Float(
        string="Max Volume Capacity (m³)",
        digits=(12, 2),
        default=0.0,
        help="Kapasitas volume kubikasi kargo maksimum dalam satuan meter kubik (m³)",
    )
    state = fields.Selection(
        selection=VEHICLE_STATE_SELECTION,
        string="Status",
        default=VEHICLE_STATE_AVAILABLE,
        required=True,
        help="Kondisi operasional armada logistik",
    )

    _sql_constraints = [
        (
            "license_plate_unique",
            "unique(license_plate)",
            "Nomor plat polisi kendaraan harus unik!",
        ),
    ]

    @api.constrains("max_weight", "max_volume")
    def _check_capacities(self):
        for record in self:
            if record.max_weight < 0:
                raise ValidationError(
                    _("Kapasitas muatan berat maksimum tidak boleh bernilai negatif!")
                )
            if record.max_volume < 0:
                raise ValidationError(
                    _("Kapasitas volume kubikasi kargo tidak boleh bernilai negatif!")
                )
```

### 3. Matriks Hak Akses Keamanan (`security/ir.model.access.csv`)
```csv
access_wms_vehicle_dispatcher,wms.vehicle.dispatcher,model_wms_vehicle,group_wms_dispatcher,1,1,1,1
access_wms_vehicle_manager,wms.vehicle.manager,model_wms_vehicle,group_wms_manager,1,1,1,1
access_wms_vehicle_system,wms.vehicle.system,model_wms_vehicle,base.group_system,1,1,1,1
access_wms_vehicle_operator,wms.vehicle.operator,model_wms_vehicle,group_wms_operator,1,0,0,0
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Penulisan format plat nomor yang tidak konsisten (misal huruf kecil vs huruf besar, spasi berlebih). | Low | Standarisasi input dapat diterapkan dengan striping spasi atau penanganan otomatis huruf besar (*uppercase*) pada method write/create. |
| Duplikasi data supir atau penugasan supir yang salah (*driver_id*). | Low | Membatasi domain `driver_id` dengan filter `[('is_company', '=', False)]` agar hanya mitra individu/personel yang dapat dipilih sebagai supir. |
| Pengguna operator tanpa wewenang mencoba mengubah status armada. | Medium | Dibatasi secara tegas melalui `ir.model.access.csv` di mana `group_wms_operator` hanya memiliki hak baca (*read-only*). |

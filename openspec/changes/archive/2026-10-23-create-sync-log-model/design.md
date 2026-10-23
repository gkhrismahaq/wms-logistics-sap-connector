# Design Document: Create Sync Log Model

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | create-sync-log-model                         |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `sap.sync.log`                                |

## Context
Sistem WMS logistik Two-Tier mengandalkan Odoo 17 sebagai lapis operasional fisik gudang dan SAP sebagai sistem ERP finansial tingkat atas. Seluruh interaksi pertukaran data (seperti sinkronisasi master material, rekanan bisnis, pesanan masuk, dan surat jalan keluar) membutuhkan rekaman audit yang persisten dan dapat dilacak. Modul dasar `wms_sap_connector` telah siap dari change sebelumnya, sehingga tahap ini memfokuskan pada penyediaan fondasi model data ORM Odoo `sap.sync.log`.
> **Reference:** Lihat [proposal.md](proposal.md) dan [tsd.md](../../docs/tsd.md) — Bagian 3.2.

## Goals / Non-Goals
### Goals
- Mendefinisikan model baru `sap.sync.log` pada direktori `addons/wms_sap_connector/models/sap_sync_log.py`.
- Mendeklarasikan seluruh atribut bidang data sesuai spesifikasi teknis SSOT `docs/tsd.md` Bagian 3.2: `name`, `sync_type`, `direction`, `payload`, `status`, `error_message`, dan `sync_date`.
- Mengimplementasikan method ORM `action_retry_sync()` dengan pengecekan integritas status (hanya record dengan status `failed` yang dapat diproses ulang) untuk mencegah duplikasi pemrosesan data.
- Menghubungkan paket model ke sistem inisialisasi Odoo melalui `addons/wms_sap_connector/models/__init__.py` dan `addons/wms_sap_connector/__init__.py`.

### Non-Goals
- Pendefinisian file hak akses sekuriti `security/ir.model.access.csv` dan grup otorisasi `security/security.xml` (dijadwalkan pada change terpisah `setup-wms-security-groups`).
- Pembuatan antarmuka visual XML Tree, Form, Search view, serta menu action Odoo (dijadwalkan pada change `ui-backend-sync-log-views`).
- Pembuatan endpoint HTTP controller atau webhook REST API penghubung SAP (dijadwalkan pada fase integrasi API).

## Decisions (ADR)
### 1. Struktur Model Modular dalam Sub-paket `models/`
- **Rationale:** Mengadopsi pedoman arsitektur modular resmi Odoo 17 dengan memisahkan model ke dalam direktori `models/` dan file terisolasi `sap_sync_log.py`. Pendekatan ini menjaga prinsip Clean Architecture (*Single Responsibility Principle*) agar modul siap diekspansi untuk model WMS lainnya.
- **Alternatives Considered:** Mendeklarasikan kelas model langsung pada file root atau menggabungkannya dalam satu file monolitik `models.py`. Opsi ini ditolak karena mengurangi keterbacaan kode dan menyulitkan kolaborasi saat domain model semakin berkembang.
- **Consequences:** Memerlukan konfigurasi impor dua tingkat pada file Python inisialisasi modul (`__init__.py` modul utama mengimpor sub-paket `models`, dan `models/__init__.py` mengimpor `sap_sync_log`).

### 2. Standardisasi Tipe Data dan Nilai Enumerasi (`Selection`)
- **Rationale:** Memastikan nilai untuk field `sync_type`, `direction`, dan `status` dibatasi secara ketat melalui Odoo `fields.Selection`. Hal ini mencegah inkonsistensi string data transaksi yang dikirimkan oleh berbagai proses background worker maupun endpoint API integrasi.
- **Alternatives Considered:** Menggunakan field bertipe `fields.Char` dengan validasi bebas. Opsi ini ditolak karena rentan terhadap galat tipografi dan menyulitkan agregasi query status pada PostgreSQL.
- **Consequences:** Penambahan jenis sinkronisasi baru di masa depan harus didaftarkan secara eksplisit ke dalam definisi opsi `sync_type` pada model.

### 3. Validasi Status pada Method `action_retry_sync()`
- **Rationale:** Pemicuan pengiriman ulang (*retry*) hanya valid dilakukan terhadap transaksi yang tercatat berstatus `failed`. Jika dipanggil pada transaksi dengan status `success` atau `pending`, sistem secara tegas membangkitkan `UserError` guna mencegah duplikasi posting transaksi ke server SAP (prinsip idempotensi).
- **Alternatives Considered:** Mengizinkan pengiriman ulang pada setiap status tanpa batasan kondisi. Opsi ini ditolak karena berisiko tinggi menimbulkan inkonsistensi data akuntansi dan inventori ganda di sisi SAP.
- **Consequences:** Logika eksternal yang memanggil method retry wajib memastikan record berada pada kondisi `failed` sebelum menjalankan proses ulang.

## Technical Architecture & Data Schema
Rancangan struktur file modul yang akan dibentuk:
```text
addons/wms_sap_connector/
├── __init__.py
├── __manifest__.py
└── models/
    ├── __init__.py
    └── sap_sync_log.py
```

Rancangan deklarasi model Python pada `addons/wms_sap_connector/models/sap_sync_log.py`:
```python
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SapSyncLog(models.Model):
    _name = 'sap.sync.log'
    _description = 'SAP Synchronization Audit Log'
    _order = 'sync_date desc, id desc'

    name = fields.Char(
        string='Transaction Reference',
        required=True,
        copy=False,
        index=True,
        help='Unique reference code or identifier for this synchronization event.'
    )
    sync_type = fields.Selection([
        ('master_product', 'Master Product / Material'),
        ('master_partner', 'Master Partner / Vendor / Customer'),
        ('inbound_po', 'Inbound Purchase Order'),
        ('outbound_so', 'Outbound Sales Delivery'),
    ], string='Sync Type', required=True, index=True)
    direction = fields.Selection([
        ('inbound', 'Inbound (SAP -> Odoo)'),
        ('outbound', 'Outbound (Odoo -> SAP)'),
    ], string='Direction', required=True, index=True)
    payload = fields.Text(
        string='Payload (JSON)',
        help='Full raw JSON payload exchanged between systems.'
    )
    status = fields.Selection([
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Status', default='pending', required=True, index=True)
    error_message = fields.Text(
        string='Error Message',
        help='Detailed failure message or stack trace if the sync failed.'
    )
    sync_date = fields.Datetime(
        string='Sync Date',
        default=fields.Datetime.now,
        required=True,
        index=True,
        help='Timestamp when the sync transaction was recorded.'
    )

    def action_retry_sync(self):
        """Reset failed synchronization logs back to pending status for re-execution."""
        for record in self:
            if record.status != 'failed':
                raise UserError(_("Only failed synchronization logs can be retried."))
            record.write({
                'status': 'pending',
                'error_message': False,
            })
        return True
```

Rancangan pendaftaran modul pada `addons/wms_sap_connector/models/__init__.py`:
```python
# -*- coding: utf-8 -*-
from . import sap_sync_log
```

Rancangan pembaruan pada `addons/wms_sap_connector/__init__.py`:
```python
# -*- coding: utf-8 -*-
from . import models
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Akumulasi volume data log yang sangat besar akibat penyimpanan payload JSON teks penuh | Medium | Menambahkan pengindeksan database pada bidang `sync_date`, `status`, `sync_type`, dan `name` guna menjaga efisiensi query, serta menyiapkan strategi archiving log pada fase operasional lanjut. |
| Percobaan pemicuan retry pada transaksi yang sudah berhasil (*duplicate sync*) | High | Menerapkan validasi ketat pada method `action_retry_sync()` yang langsung melemparkan `UserError` jika status transaksi bukan `failed`. |
| Ketidaksesuaian nilai pilihan (*selection key*) terhadap payload integrasi SAP di fase mendatang | Low | Nilai kunci seleksi telah diselaraskan 100% dengan kontrak SSOT pada `docs/tsd.md` Bagian 3.2 dan Bagian 3.5. |

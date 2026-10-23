# Design Document: Setup Wms Security Groups

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | setup-wms-security-groups                     |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `sap.sync.log`                                |

## Context
Modul `wms_sap_connector` telah memiliki model ORM `sap.sync.log` yang diinisialisasi pada change sebelumnya (`create-sync-log-model`). Namun, modul belum mendefinisikan grup keamanan pengguna (`res.groups`) maupun tabel Access Control List (`security/ir.model.access.csv`). Pada arsitektur Odoo 17, model data yang tidak memiliki deklarasi hak akses dalam `ir.model.access.csv` akan memicu peringatan sekuriti dan menolak akses ORM bagi pengguna biasa.

Selain itu, operasional WMS Two-Tier membutuhkan pembatasan kewenangan yang tegas antara aktivitas fisik di lantai gudang (Warehouse Operator), pengaturan penugasan armada dan dokumen pengiriman (Logistics Dispatcher), serta pengelolaan administratif dan penanganan insiden pertukaran data integrasi SAP (Warehouse Manager) sesuai referensi SSOT [tsd.md](../../docs/tsd.md) (Bagian 3.6).

## Goals / Non-Goals

### Goals
- Mendefinisikan kategori modul keamanan `module_category_wms_logistics` pada `ir.module.category` untuk mengelompokkan hak akses WMS pada antarmuka manajemen pengguna Odoo.
- Mengonfigurasi tiga grup keamanan pengguna (`res.groups`) pada `addons/wms_sap_connector/security/security.xml`:
  1. `group_wms_operator` (Warehouse Operator / Staf Gudang)
  2. `group_wms_dispatcher` (Logistics Dispatcher / Staf Logistik)
  3. `group_wms_manager` (Warehouse Manager / Kepala Gudang) dengan pewarisan grup (`implied_ids`) terhadap operator dan dispatcher.
- Mengonfigurasi Access Control List pada `addons/wms_sap_connector/security/ir.model.access.csv` untuk mengamankan model `sap.sync.log` (`model_sap_sync_log`).
- Memperbarui `addons/wms_sap_connector/__manifest__.py` dengan mendaftarkan file sekuriti pada kunci `data` dalam urutan deklarasi yang valid.

### Non-Goals
- Tidak mengonfigurasi Record Rules (`ir.rule`) berbasis domain filter multi-warehouse atau per-cabang pada change ini (akan dialokasikan saat model gudang/lokasi diperluas).
- Tidak membuat atau mengubah view XML antarmuka pengguna (Tree, Form, Action Menu) untuk model `sap.sync.log` (lingkup ini dikerjakan pada change berikutnya `ui-backend-sync-log-views`).
- Tidak memodifikasi skema data atau method Python pada `sap.sync.log`.

## Decisions (ADR)

### 1. Struktur Kategori Modul dan Hierarki Grup Keamanan Odoo 17
- **Rationale:** Mengelompokkan grup sekuriti di bawah kategori khusus `module_category_wms_logistics` mempermudah administrator dalam mengelola hak akses pengguna pada menu *Settings > Users & Companies > Users*. Penerapan hierarki peran melalui atribut `implied_ids` pada `group_wms_manager` memastikan Kepala Gudang secara otomatis memiliki seluruh hak dari Operator Gudang dan Staf Logistik tanpa perlu menandai setiap kotak centang secara individual.
- **Alternatives Considered:**
  - Menggunakan grup standar Odoo `stock.group_stock_user` dan `stock.group_stock_manager`: Ditolak karena operasional WMS Logistik Two-Tier memiliki pembagian peran yang spesifik (seperti Dispatcher untuk armada logistik dan Manager untuk penanganan audit log SAP) yang tidak terakomodasi dalam peran bawaan stok.
  - Struktur peran datar (*flat roles*) tanpa pewarisan `implied_ids`: Ditolak karena meningkatkan overhead administrasi dan potensi inkonsistensi otorisasi.
- **Consequences:** Penugasan `group_wms_manager` memberikan akses menyeluruh ke seluruh fungsi WMS internal.

### 2. Matriks Hak Akses Model sap.sync.log pada ir.model.access.csv
- **Rationale:** Model `sap.sync.log` menyimpan rekam jejak sensitif pertukaran data dua arah dengan sistem SAP. Berdasarkan SSOT [tsd.md](../../docs/tsd.md) Bagian 3.6, hanya peran manajerial yang berwenang menindaklanjuti kegagalan sinkronisasi. Oleh sebab itu, `group_wms_manager` dan `base.group_system` diberikan izin CRUD penuh (1, 1, 1, 1). Sebaliknya, `group_wms_operator` dan `group_wms_dispatcher` diberikan izin baca (*read-only*: 1, 0, 0, 0) agar tetap dapat memantau status dokumen tanpa risiko memodifikasi atau menghapus jejak audit. Pengguna umum di luar grup tersebut tidak memiliki izin akses sama sekali.
- **Alternatives Considered:** Memberikan hak tulis/modifikasi kepada `group_wms_operator`: Ditolak karena manipulasi payload atau eksekusi retry tanpa otorisasi berisiko menyebabkan inkonsistensi data dengan SAP.
- **Consequences:** Penanganan galat integrasi dan pembersihan data log strictly terisolasi untuk Manajer Gudang dan Admin Sistem.

### 3. Urutan Pemuatan Data pada Manifest Modul
- **Rationale:** Framework ORM Odoo membaca daftar file data pada manifest secara berurutan. File `security/ir.model.access.csv` merujuk pada XML ID grup yang dideklarasikan di `security/security.xml` (misalnya `wms_sap_connector.group_wms_manager`). Jika urutannya terbalik, Odoo akan mengalami kegagalan instalasi dengan galat `ValueError: External ID not found`.
- **Alternatives Considered:** Menggabungkan deklarasi ACL ke dalam file XML menggunakan record `ir.model.access`: Ditolak karena konvensi Odoo 17 merekomendasikan format CSV untuk ACL demi kemudahan pembacaan dan pemeliharaan matriks hak akses.
- **Consequences:** Manifest `__manifest__.py` wajib mendaftarkan `security/security.xml` sebelum `security/ir.model.access.csv`.

## Technical Architecture & Data Schema

### 1. Deklarasi Grup Keamanan (`addons/wms_sap_connector/security/security.xml`)
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="0">
        <!-- Kategori Modul WMS Logistics -->
        <record id="module_category_wms_logistics" model="ir.module.category">
            <field name="name">WMS Logistics</field>
            <field name="description">Manajemen Hak Akses WMS &amp; Integrasi SAP</field>
            <field name="sequence">20</field>
        </record>

        <!-- Grup: Warehouse Operator / Staf Gudang -->
        <record id="group_wms_operator" model="res.groups">
            <field name="name">Warehouse Operator</field>
            <field name="category_id" ref="module_category_wms_logistics"/>
            <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
            <field name="comment">Akses operasional pemindaian barcode, dokumen picking, dan alokasi rak.</field>
        </record>

        <!-- Grup: Logistics Dispatcher / Staf Logistik -->
        <record id="group_wms_dispatcher" model="res.groups">
            <field name="name">Logistics Dispatcher</field>
            <field name="category_id" ref="module_category_wms_logistics"/>
            <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
            <field name="comment">Akses pengelolaan armada, penugasan supir, cetak surat jalan, dan POD.</field>
        </record>

        <!-- Grup: Warehouse Manager / Kepala Gudang -->
        <record id="group_wms_manager" model="res.groups">
            <field name="name">Warehouse Manager</field>
            <field name="category_id" ref="module_category_wms_logistics"/>
            <field name="implied_ids" eval="[(4, ref('group_wms_operator')), (4, ref('group_wms_dispatcher'))]"/>
            <field name="comment">Akses administratif menyeluruh gudang dan penanganan log galat integrasi SAP.</field>
        </record>
    </data>
</odoo>
```

### 2. Matriks Hak Akses Model (`addons/wms_sap_connector/security/ir.model.access.csv`)
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_sap_sync_log_manager,sap.sync.log.manager,model_sap_sync_log,group_wms_manager,1,1,1,1
access_sap_sync_log_system,sap.sync.log.system,model_sap_sync_log,base.group_system,1,1,1,1
access_sap_sync_log_operator,sap.sync.log.operator,model_sap_sync_log,group_wms_operator,1,0,0,0
access_sap_sync_log_dispatcher,sap.sync.log.dispatcher,model_sap_sync_log,group_wms_dispatcher,1,0,0,0
```

### 3. Pendaftaran Manifest (`addons/wms_sap_connector/__manifest__.py`)
```python
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
    ],
```

## Risks & Trade-offs

| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Kesalahan referensi XML ID model Odoo pada CSV (`model_sap_sync_log`) | Medium | Memastikan ID model dibentuk secara tepat dari nama teknis Odoo (`model_` + `sap_sync_log` dengan tanda titik diganti garis bawah). |
| Urutan muat data terbalik pada manifest | High | Menempatkan `security/security.xml` di atas `security/ir.model.access.csv` dalam list `data` manifest. |
| Pengguna operator tidak dapat mengakses modul sama sekali | Low | Menyertakan `base.group_user` (Internal User) pada `implied_ids` grup operator dan dispatcher agar memiliki hak dasar sistem Odoo. |

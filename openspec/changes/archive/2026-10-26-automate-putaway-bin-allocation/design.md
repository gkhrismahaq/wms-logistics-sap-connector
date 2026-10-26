# Design Document: Automate Putaway Bin Allocation

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | automate-putaway-bin-allocation               |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `stock.picking`, `stock.move`, `stock.move.line`, `stock.putaway.rule`, `stock.location` |

## Context
Pada tahapan sebelumnya (`api-receive-sap-purchase-order`), sistem telah berhasil menerima dokumen pesanan pembelian dari SAP dan secara otomatis menerbitkan dokumen `stock.picking` (tipe operasi `incoming`) berstatus `assigned`. Saat ini, lokasi tujuan yang tercatat pada level header dokumen adalah lokasi gudang induk (`location_dest_id = DCLOW/Stock`).

Agar staf operasional gudang (*picker/packer*) dapat menempatkan barang langsung ke lorong dan rak (*bin/rack*) penyimpanan fisik secara optimal dan cepat tanpa harus menebak lokasi kosong atau membiarkan barang menumpuk di lantai docking penerimaan, diperlukan alokasi rak otomatis berbasis aturan penempatan (*Putaway Rule*) standar Odoo 17 yang terintegrasi secara mulus pada alur inbound.

## Goals / Non-Goals
### Goals
- Mengintegrasikan evaluasi aturan penempatan rak otomatis (`stock.putaway.rule`) pada alur pembuatan dan konfirmasi dokumen penerimaan barang masuk (`create_inbound_from_sap`).
- Memastikan baris detail operasi fisik (`stock.move.line`) memuat lokasi tujuan rak/bin fisik spesifik (contoh: `DCLOW/Stock/Shelf 1`) saat status picking menjadi `assigned` (Ready).
- Menyediakan data konfigurasi awal (*data seed* XML) aturan putaway (`data/stock_putaway_data.xml`) yang memetakan material master SAP ke rak gudang yang sesuai.
- Menetapkan hak akses model `stock.putaway.rule` pada `security/ir.model.access.csv` untuk operator gudang dan manajer gudang.
- Memastikan visibilitas lokasi rak tujuan pada antarmuka pengguna dokumen picking formulir penerimaan barang.

### Non-Goals
- Tidak membuat model penempatan baru dari nol; memanfaatkan model standar Odoo 17 `stock.putaway.rule` yang sudah teruji dan stabil.
- Tidak mengimplementasikan pengiriman sinyal webhook konfirmasi Goods Receipt ke SAP pada change ini (hal ini merupakan ruang lingkup change berikutnya `webhook-notify-sap-goods-receipt`).
- Tidak mengubah skema tabel model `stock.location` yang telah memiliki bidang data `barcode`, `sap_plant_code`, dan `sap_sloc_code`.

## Decisions (ADR)
### 1. Pemanfaatan Model Standar Odoo 17 `stock.putaway.rule` Dibanding Membuat Engine Kustom
- **Rationale:** Odoo 17 memiliki arsitektur *Putaway Strategy* bawaan (`stock.location._get_putaway_strategy`) yang sangat terintegrasi dengan `stock.move` dan `stock.move.line`. Saat method `action_confirm()` atau `action_assign()` dipanggil, sistem secara otomatis mengevaluasi aturan putaway yang aktif berdasarkan produk atau kategori produk yang masuk ke lokasi gudang penampung.
- **Alternatives Considered:** Membuat model kustom `wms.putaway.rule`. Opsi ini ditolak keras karena memicu redundansi kode (*reinventing the wheel*), memerlukan pemeliharaan logika tambahan, dan tidak terintegrasi secara otomatis dengan modul barcode scanner bawaan Odoo.
- **Consequences:** Arsitektur tetap bersih (*Clean Architecture*), mematuhi standar Odoo enterprise, dan meminimalkan potensi regresi.

### 2. Alokasi Rak Spesifik pada Layer `stock.move.line`
- **Rationale:** Pada arsitektur inventori Odoo 17, `stock.move` merepresentasikan komitmen perpindahan kuantitas logis (masuk ke gudang induk), sedangkan penempatan fisik nyata pada rak/bin lorong tertentu dicatat pada baris operasi detail `stock.move.line`. Dengan memastikan baris move line terbentuk dan diarahkan ke lokasi rak spesifik, staf gudang langsung melihat target rak fisik pada layar pemindai barcode / formulir picking.
- **Alternatives Considered:** Mengubah `stock.move.location_dest_id` langsung ke lokasi rak fisik. Opsi ini ditolak karena menyulitkan skenario ketika 1 pesanan barang dalam jumlah besar harus dipecah (*split*) ke dalam beberapa rak yang berbeda saat kapasitas rak pertama penuh.
- **Consequences:** Mendukung skalabilitas tata letak gudang, fleksibilitas penempatan barang, dan akurasi pelacakan persediaan multi-rak.

### 3. Penyediaan Data Konfigurasi Putaway Awal Melalui XML Data
- **Rationale:** Modul harus langsung siap diuji dan digunakan pada lingkungan dev/staging tanpa mewajibkan pengguna melakukan konfigurasi manual aturan putaway satu per satu melalui antarmuka web.
- **Alternatives Considered:** Mengandalkan pembuatan aturan putaway secara manual via UI Odoo setelah instalasi modul. Opsi ini ditolak karena menghambat pengujian integrasi otomatis dan simulasi end-to-end.
- **Consequences:** Lingkungan pengujian dan demonstrasi menjadi sepenuhnya otomatis dan dapat direproduksi (*reproducible*).

## Technical Architecture & Data Schema

### 1. Skema Data Seed XML Aturan Putaway (`data/stock_putaway_data.xml`)
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <!-- Putaway Rule: MAT-KOPI-01 diarahkan ke Shelf 1 -->
        <record id="putaway_rule_kopi_shelf1" model="stock.putaway.rule">
            <field name="product_id" model="product.product"
                   eval="obj().env['product.product'].search([('sap_material_code', '=', 'MAT-KOPI-01')], limit=1).id"/>
            <field name="location_in_id" model="stock.location"
                   eval="obj().env['stock.location'].search([('complete_name', '=', 'DCLOW/Stock')], limit=1).id"/>
            <field name="location_out_id" model="stock.location"
                   eval="obj().env['stock.location'].search([('complete_name', '=', 'DCLOW/Stock/Shelf 1')], limit=1).id"/>
            <field name="sequence">10</field>
        </record>
    </data>
</odoo>
```

### 2. Logika Pembuatan Move Line & Putaway pada `stock.picking`
Pada method `create_inbound_from_sap` di `models/stock_picking.py`:
Saat `picking.action_confirm()` dipanggil pada dokumen incoming, Odoo secara otomatis memicu pembuatan `stock.move.line` yang memanggil `location_dest_id._get_putaway_strategy(product, qty)`. Jika aturan cocok, `move_line.location_dest_id` otomatis diisi dengan `Shelf 1` atau `Shelf 2`. Jika belum ada `move_line`, sistem memastikan move lines di-generate atau dipastikan terhubung dengan lokasi tujuan putaway.

### 3. Matriks Akses Keamanan (`security/ir.model.access.csv`)
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_stock_putaway_rule_operator,stock.putaway.rule.operator,stock.model_stock_putaway_rule,wms_sap_connector.group_wms_operator,1,0,0,0
access_stock_putaway_rule_manager,stock.putaway.rule.manager,stock.model_stock_putaway_rule,wms_sap_connector.group_wms_manager,1,1,1,1
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Material baru dari SAP belum memiliki aturan putaway yang terdaftar | Low | Sistem secara otomatis mengembalikan *fallback* lokasi tujuan ke lokasi stok induk gudang penampung (`DCLOW/Stock`) sehingga alur penerimaan barang tidak pernah terblokir. |
| Lokasi rak tujuan dinonaktifkan atau dihapus | Medium | Odoo putaway engine secara hierarkis memeriksa keabsahan lokasi; jika lokasi rak tidak valid, sistem kembali ke lokasi induk yang aktif. |
| Ambiguitas hak akses antara operator dan manajer gudang | Low | Didefinisikan secara tegas pada `security/ir.model.access.csv`: Operator hanya memiliki hak baca (read-only), sedangkan Manajer Gudang memiliki hak kelola penuh (CRUD). |

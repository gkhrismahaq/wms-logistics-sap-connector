# Design Document: Webhook Notify SAP Goods Receipt

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | webhook-notify-sap-goods-receipt              |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `stock.picking`, `sap.sync.log`, `res.config.settings` |

## Context
Pada alur penerimaan barang masuk (*Inbound*), dokumen `stock.picking` (tipe operasi `incoming`) dibuat dari pesanan pembelian SAP dengan status `assigned` dan rak tujuan telah teralokasi otomatis (*Putaway Rule*). Saat staf gudang selesai memeriksa fisik barang dan menekan tombol validasi, dokumen bertransisi menjadi `done`.

Sesuai spesifikasi arsitektur Two-Tier WMS ([tsd.md](../../docs/tsd.md) — Bagian 2.2.2 & 3.5.2), Odoo harus secara otomatis mengirimkan notifikasi webhook HTTP POST ke SAP Upper Line (`POST /api/sap/goods-receipt`) untuk konfirmasi penerimaan fisik, dan menyimpan respon simulasi jurnal akuntansi SAP (`sap_accounting_log`) ke tabel `sap.sync.log`.

## Goals / Non-Goals
### Goals
- Meng-override lifecycle penyelesaian transfer pada model `stock.picking` untuk secara otomatis mengeksekusi pengiriman webhook ke `{sap_base_url}/api/sap/goods-receipt` saat dokumen incoming bertransisi ke status `done`.
- Mengirimkan payload JSON sesuai kontrak: `sap_doc_number`, `status: "GOODS_RECEIVED"`, `received_date`, dan `warehouse_code`.
- Mengimplementasikan mekanisme pengiriman *fail-safe* (*non-blocking*): kegagalan jaringan atau timeout ke SAP tidak membatalkan (*rollback*) transfer fisik barang di Odoo.
- Mendokumentasikan payload request dan response (termasuk objek `sap_accounting_log`) ke model `sap.sync.log` dengan `direction = 'outbound'` dan `sync_type = 'inbound_po'`.
- Memperbarui `sap_sync_status` pada `stock.picking` (`synced` jika berhasil, `failed` jika gagal).
- Menyediakan method dan tombol "Retry SAP Webhook" pada formulir picking agar pengguna dapat mengirim ulang saat status `failed`.

### Non-Goals
- Tidak mengimplementasikan endpoint penerima webhook di sisi Odoo (endpoint `/api/sap/goods-receipt` berada pada host eksternal SAP/FastAPI).
- Tidak memodifikasi alur webhook outbound untuk pesanan penjualan / pengantaran (*Goods Issue* / Delivery Order) pada change ini (hal tersebut berada pada Fase 4).

## Decisions (ADR)
### 1. Eksekusi Webhook pada Hook ORM `_action_done` Dibanding `button_validate`
- **Rationale:** Di Odoo 17, `_action_done()` adalah method inti ORM yang dieksekusi setiap kali perpindahan stok selesai divalidasi ke status `done`, baik dipicu melalui antarmuka formulir web, barcode scanner genggam, maupun pemanggilan API.
- **Alternatives Considered:** Meng-override hanya method `button_validate()`. Opsi ini ditolak karena validasi melalui barcode scanner atau alur terotomatisasi lainnya tidak memanggil `button_validate()`, sehingga berisiko melewatkan pengiriman webhook.
- **Consequences:** Notifikasi webhook terjamin terkirim secara konsisten dari seluruh kanal validasi transfer.

### 2. Pendekatan Non-Blocking & Resilient Network Handling
- **Rationale:** Perpindahan barang fisik di lantai gudang adalah fakta operasional nyata yang tidak boleh tertunda hanya karena server SAP remote sedang tidak dapat dijangkau (*offline* atau *timeout*). Dengan membungkus panggilan HTTP dalam blok `try...except`, status stok fisik tetap tersimpan `done`, dokumen ditandai `failed`, dan log kesalahan dicatat secara lengkap.
- **Alternatives Considered:** Melempar eksepsi `UserError` saat webhook gagal agar transfer di-rollback. Opsi ini ditolak keras karena menghentikan operasional fisik gudang dan memicu ketidaksesuaian stok nyata dengan stok sistem.
- **Consequences:** Sistem memiliki ketahanan tinggi (*high availability*) dan mendukung rekonsiliasi asinkron.

### 3. Penyimpanan Respon Jurnal Akuntansi SAP pada `sap.sync.log`
- **Rationale:** Model `sap.sync.log` telah dirancang untuk mencatat payload pertukaran data dua arah. Menyimpan respon `sap_accounting_log` ke dalam field `payload` pada record log dengan `direction = 'outbound'` memberikan jejak audit keuangan yang transparan tanpa perlu menambah tabel baru (*anti-redundansi*).
- **Alternatives Considered:** Membuat tabel terpisah `sap.accounting.log`. Ditolak karena menambah kompleksitas skema tanpa memberikan nilai tambah signifikan.
- **Consequences:** Arsitektur tetap ramping (*Clean Architecture*) dan mematuhi SSOT.

## Technical Architecture & Data Schema

### 1. Payload Transmisi Webhook Outbound
```json
{
  "sap_doc_number": "PO-SAP-2026-001",
  "status": "GOODS_RECEIVED",
  "received_date": "2026-10-26T11:00:00Z",
  "warehouse_code": "DCLOW"
}
```

### 2. Logika Pemanggilan Webhook pada `models/stock_picking.py`
```python
def _action_done(self):
    res = super()._action_done()
    for picking in self:
        if (
            picking.picking_type_id.code == PICKING_TYPE_CODE_INCOMING
            and picking.sap_doc_number
        ):
            picking._send_sap_goods_receipt_webhook()
    return res


def action_send_sap_goods_receipt_webhook(self):
    """Manual trigger to re-send Goods Receipt webhook to SAP."""
    self.ensure_one()
    return self._send_sap_goods_receipt_webhook()
```

### 3. Penambahan Tombol Aksi pada `views/stock_picking_views.xml`
```xml
<xpath expr="//header" position="inside">
    <button name="action_send_sap_goods_receipt_webhook"
            string="Retry SAP Webhook"
            type="object"
            class="btn-secondary"
            invisible="state != 'done' or sap_sync_status == 'synced' or not sap_doc_number"/>
</xpath>
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Server SAP mengalami latency tinggi / timeout | Medium | Mengatur `timeout=10` pada panggilan HTTP `requests.post()` dan menangkap `requests.exceptions.RequestException` secara elegan tanpa memutus alur ORM. |
| Pengguna mengirimkan retry berkali-kali secara manual | Low | Endpoint SAP didesain idempoten; status Odoo langsung dimutakhirkan ke `synced` begitu respon sukses pertama diterima. |
| Parameter konfigurasi SAP belum disetel di Settings | Medium | Sistem memeriksa keberadaan `sap_base_url` sebelum melakukan koneksi; jika belum dikonfigurasi, sistem mencatat pesan peringatan informatif ke `sap.sync.log` dan menandai status `failed`. |

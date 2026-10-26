# Design Document: Webhook Notify SAP Goods Issue

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | webhook-notify-sap-goods-issue                |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `stock.picking`, `sap.sync.log`               |

## Context
Pada kapabilitas sebelumnya (`feature-driver-proof-of-delivery`), dokumen transfer pengeluaran kargo (`stock.picking` bertipe `outgoing`) telah dilengkapi dengan field bukti serah terima digital (`proof_of_delivery`, `pod_signed_by`, `pod_timestamp`, dan `has_pod`). Pada alur logistik *Two-Tier ERP*, penyelesaian fisik pengiriman di Odoo harus disinkronkan ke SAP Upper Line melalui webhook *Goods Issue (GI)* (`POST /api/sap/goods-issue`) agar sistem SAP mencatatkan pemotongan stok finansial dan membebankan Harga Pokok Penjualan (HPP). Respons simulasi akuntansi SAP (`sap_accounting_log`) tersebut harus terekam secara persisten ke dalam `sap.sync.log` tanpa mengganggu kelancaran proses pergudangan jika terjadi kegagalan transmisi.

## Goals / Non-Goals

### Goals
- Mengimplementasikan method transmisi webhook HTTP POST `_send_sap_goods_issue_webhook()` pada model `stock.picking` yang mengirimkan data penyerahan kargo ke SAP.
- Memicu transmisi webhook secara otomatis pada dua titik siklus hidup (*lifecycle hooks*):
  1. Saat dokumen `stock.picking` divalidasi ke status `done` dan bukti POD sudah lengkap (`has_pod == True`).
  2. Saat dokumen transfer sudah berstatus `done` dan bukti POD baru saja diunggah menyusul (`write()` pada field POD).
- Menyediakan tombol aksi manual `"Send Goods Issue to SAP"` (`action_send_sap_goods_issue_webhook`) pada header formulir Delivery Order untuk pengiriman ulang jika terjadi kegagalan sinkronisasi.
- Menyimpan respons lengkap dari SAP, terutama objek `sap_accounting_log`, ke dalam `sap.sync.log` dengan `sync_type='outbound_so'` dan `direction='outbound'`.
- Memastikan eksekusi transmisi bersifat *fail-safe* dan *non-blocking* (tidak membatalkan transaksi mutasi stok Odoo jika jaringan ke SAP bermasalah).

### Non-Goals
- Tidak mengimplementasikan mock server FastAPI SAP secara mandiri (hal tersebut dijadwalkan secara terpisah pada Fase 5, Capability 5.1: `setup-mock-sap-service`).
- Tidak mengubah skema data master produk, partner, atau model armada `wms.vehicle`.
- Tidak mengubah format visual laporan PDF Surat Jalan yang telah distandardisasi sebelumnya.

## Decisions (ADR)

### 1. Dual-Trigger Hook Strategy (Validation Done & Late POD Upload)
- **Rationale:** Dalam operasional logistik lapangan, supir sering kali memvalidasi pengantaran saat tiba di lokasi, namun foto fisik surat jalan atau tanda tangan digital penerima baru diunggah beberapa menit/jam kemudian setelah sinyal seluler stabil. Mengaitkan transmisi hanya pada `_action_done()` akan menyebabkan webhook tidak terkirim jika POD belum diunggah saat tombol validasi diklik. Oleh karena itu, sistem memicu webhook pada `_action_done()` (jika `has_pod == True`) DAN pada `write()` saat field POD diisi pada record yang sudah berstatus `done`.
- **Alternatives Considered:**
  - Hanya memicu pada `_action_done()`: Ditolak karena jika POD diunggah belakangan, sinkronisasi ke SAP tidak akan pernah terjadi secara otomatis.
  - Memaksa validasi `_action_done()` gagal jika POD belum diunggah: Ditolak karena melanggar fleksibilitas operasional gudang saat dispatcher perlu menyelesaikan pergerakan stok sebelum berkas fisik kembali dari armada.
- **Consequences:** Terdapat logika pengecekan kondisi pada `write()` agar tidak terjadi duplikasi panggilan webhook jika data POD diunggah berulang kali pada picking yang sudah tersinkronisasi (`sap_sync_status == 'synced'`).

### 2. Fail-Safe, Non-Blocking Execution Pattern
- **Rationale:** Transmisi HTTP keluar menuju sistem eksternal memiliki risiko kegagalan jaringan (*timeout*, *connection refused*, HTTP 5xx). Proses pergudangan fisik barang tidak boleh terhambat oleh keterlambatan atau gangguan pada server SAP.
- **Alternatives Considered:**
  - Membungkus HTTP request dalam database transaction Odoo dan melempar `UserError` saat gagal: Ditolak karena pembatalan mutasi stok fisik akibat gangguan server eksternal sangat merugikan efisiensi gudang.
- **Consequences:** Seluruh panggilan `requests.post()` dibungkus dalam blok `try...except`. Hasil kegagalan dicatat ke field `sap_sync_status = 'failed'` dan entri log di `sap.sync.log` berstatus `failed` dengan detail `error_message`, sehingga operator gudang dapat menekan tombol aksi manual `"Send Goods Issue to SAP"` untuk melakukan pengiriman ulang.

### 3. Explicit Payload Formatting & Accounting Log Capture
- **Rationale:** Endpoint SAP `/api/sap/goods-issue` mengharapkan struktur payload JSON yang memuat `sap_doc_number`, `status: "GOODS_ISSUED"`, `issued_date`, `receiver_name`, dan `has_pod: true`. Sistem SAP mengembalikan respons yang menyertakan data akuntansi finansial `sap_accounting_log` (berisi nomor `journal_entry`, `debit_account`, `credit_account`, dan `financial_status`).
- **Alternatives Considered:**
  - Menyimpan respons teks mentah tanpa struktur log: Ditolak karena menyulitkan audit keuangan saat rekonsiliasi persediaan akhir bulan.
- **Consequences:** Respons JSON dari SAP disimpan seutuhnya pada field `payload` di tabel `sap.sync.log` dengan `sync_type='outbound_so'` dan `direction='outbound'`.

## Technical Architecture & Data Schema

### 1. Konstanta Tambahan (`addons/wms_sap_connector/constants.py`)
```python
REF_PREFIX_GOODS_ISSUE = "GI"
SAP_ENDPOINT_GOODS_ISSUE = "/api/sap/goods-issue"
WEBHOOK_STATUS_GOODS_ISSUED = "GOODS_ISSUED"
```

### 2. Perluasan Model `stock.picking` (`addons/wms_sap_connector/models/stock_picking.py`)
```python
class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _send_sap_goods_issue_webhook(self):
        """Sends Goods Issue & POD confirmation webhook HTTP POST to SAP Upper Line."""
        for picking in self:
            if not picking.sap_doc_number or not picking.has_pod:
                continue

            sync_ref = picking._generate_sync_ref(REF_PREFIX_GOODS_ISSUE)
            # Retrieve base_url & token from config_parameter
            ...
            payload = {
                "sap_doc_number": picking.sap_doc_number,
                "status": WEBHOOK_STATUS_GOODS_ISSUED,
                "issued_date": (picking.pod_timestamp or fields.Datetime.now()).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "receiver_name": picking.pod_signed_by or "Penerima Kargo",
                "has_pod": bool(picking.has_pod),
            }
            # Execute requests.post with timeout, save to sap.sync.log, update sap_sync_status

    def action_send_sap_goods_issue_webhook(self):
        """Manual button action to send or retry Goods Issue webhook."""
        self.ensure_one()
        self._send_sap_goods_issue_webhook()
        return True

    def _action_done(self):
        res = super()._action_done()
        for picking in self:
            if picking.picking_type_id.code == PICKING_TYPE_CODE_OUTGOING and picking.sap_doc_number and picking.has_pod:
                picking._send_sap_goods_issue_webhook()
        return res

    def write(self, vals):
        res = super().write(vals)
        for picking in self:
            if (
                picking.picking_type_id.code == PICKING_TYPE_CODE_OUTGOING
                and picking.state == PICKING_STATE_DONE
                and picking.sap_doc_number
                and picking.has_pod
                and picking.sap_sync_status != SYNC_STATUS_SYNCED
                and any(f in vals for f in ("proof_of_delivery", "pod_signed_by"))
            ):
                picking._send_sap_goods_issue_webhook()
        return res
```

### 3. Kontrak REST Webhook Payload

**Request:**
```http
POST /api/sap/goods-issue HTTP/1.1
Host: sap-server:8000
Authorization: Bearer <SAP_API_TOKEN>
X-Odoo-API-Key: <SAP_API_TOKEN>
Content-Type: application/json

{
  "sap_doc_number": "SO-DELIV-2026-901",
  "status": "GOODS_ISSUED",
  "issued_date": "2026-10-26T17:00:00Z",
  "receiver_name": "Budi Santoso (Alfamart)",
  "has_pod": true
}
```

**Response (HTTP 200 OK):**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "message": "Goods Issue and POD acknowledged in SAP Financials",
  "sap_accounting_log": {
    "journal_entry": "JE-SAP-2026-9902",
    "posting_date": "2026-10-26",
    "debit_account": "501.001 - Harga Pokok Penjualan (HPP) (Rp 25.000.000)",
    "credit_account": "101.001 - Persediaan Barang Jadi (Rp 25.000.000)",
    "financial_status": "POSTED"
  }
}
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Server SAP offline saat transfer kargo divalidasi | Medium | Menerapkan eksekusi fail-safe non-blocking, menandai `sap_sync_status = 'failed'`, mencatat insiden ke `sap.sync.log`, dan menyediakan tombol aksi manual *"Send Goods Issue to SAP"* di antarmuka formulir. |
| Pengunggahan ulang berkas POD memicu spam webhook | Low | Menambahkan kondisi guard: webhook otomatis via `write()` hanya dieksekusi jika `sap_sync_status != 'synced'` atau dipicu secara eksplisit lewat tombol retry manual. |
| Nilai nama penerima atau timestamp POD belum terisi | Low | Menyiapkan nilai fallback otomatis menggunakan `fields.Datetime.now()` untuk timestamp dan teks representatif untuk nama penerima jika kosong. |

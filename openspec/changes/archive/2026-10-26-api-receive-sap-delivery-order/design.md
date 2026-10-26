# Design Document: API Receive SAP Delivery Order

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Change Name**    | api-receive-sap-delivery-order                |
| **Arch Pattern**   | Two-Tier Odoo WMS & SAP REST Connector        |
| **Primary Models** | `stock.picking`, `stock.move`, `res.partner`, `sap.sync.log` |

## Context
Pada integrasi Two-Tier ERP ([tsd.md](../../docs/tsd.md) — Bagian 2.2.3 & 3.5.3), transaksi penjualan dibuat dan diverifikasi status kreditnya di SAP Upper Line. Saat barang siap dikirim ke pelanggan, SAP menerbitkan instruksi pengiriman (*Sales Delivery Order*). WMS Odoo 17 harus menyediakan endpoint penerima `/api/sap/outbound/delivery` yang menerima payload JSON dari SAP dan secara otomatis mengonversinya menjadi dokumen *Delivery Order* (`stock.picking` tipe `outgoing`).

Modul `wms_sap_connector` telah memiliki fondasi autentikasi API token, pencatatan log audit `sap.sync.log`, serta model armada logistik `wms.vehicle`. Change ini menyediakan gerbang integrasi pertama pada alur keluar (*Outbound & Delivery*) sebelum penugasan armada dan pencetakan Surat Jalan dilakukan.

## Goals / Non-Goals
### Goals
- Mengimplementasikan endpoint REST API publik `POST /api/sap/outbound/delivery` pada kelas `SapOutboundController` di `addons/wms_sap_connector/controllers/main.py`.
- Menerapkan autentikasi token API (`X-Odoo-API-Key` atau `Authorization: Bearer <token>`) sesuai parameter sistem `wms_sap_connector.sap_api_token`.
- Mengimplementasikan method ORM `create_outbound_from_sap(payload_dict)` pada model `stock.picking` untuk memetakan pelanggan (`res.partner` dengan `sap_partner_code`), material produk (`product.product` dengan `sap_material_code`), dan kuantitas kargo.
- Menjamin mekanisme idempotensi: jika dokumen `stock.picking` tipe `outgoing` dengan `sap_doc_number` yang sama sudah ada, kembalikan record tersebut tanpa menerbitkan dokumen duplikat.
- Mengonfirmasi dokumen pengeluaran stok (`action_confirm()` dan `action_assign()`) agar stok tereservasi dan dokumen berstatus siap diproses (`assigned` atau `confirmed`).
- Mendokumentasikan setiap request dan response transaksi ke tabel audit `sap.sync.log` dengan tipe `outbound_so` dan arah `inbound`.
- Mengembalikan respon JSON terstruktur (HTTP 200, HTTP 400, HTTP 401).
- Menyediakan automated unit test lengkap untuk menguji seluruh jalur Happy Path, Idempotent, dan Edge Case validasi/autentikasi.

### Non-Goals
- Tidak menugaskan kendaraan armada (`vehicle_id`) dan supir (`driver_id`) pada change ini (hal tersebut merupakan lingkup change `extend-picking-dispatch-fields`).
- Tidak membuat laporan cetak Surat Jalan PDF (merupakan lingkup change `report-official-surat-jalan`).
- Tidak mengimplementasikan transmisi webhook Goods Issue ke SAP (merupakan lingkup change `webhook-notify-sap-goods-issue`).

## Decisions (ADR)
### 1. Pembuatan Kelas Controller Terdedikasi `SapOutboundController`
- **Rationale:** Mematuhi prinsip *Separation of Concerns* dan arsitektur bersih (*Clean Architecture*). Memisahkan kontroler alur pengiriman keluar (`SapOutboundController`) dari penerimaan barang masuk (`SapInboundController`) dan master data (`SapMasterDataController`) menjaga keterbacaan kode, memudahkan pemeliharaan, dan menyederhanakan pelacakan rute API.
- **Alternatives Considered:** Menambahkan rute pengiriman keluar ke dalam kelas `SapInboundController`. Ditolak karena membingungkan pemisahan domain bisnis Inbound vs Outbound.
- **Consequences:** Struktur file `controllers/main.py` tetap terorganisir dengan rapi dan modular.

### 2. Enkapsulasi Logika Bisnis Dokumen pada Model `stock.picking`
- **Rationale:** Standar arsitektur enterprise Odoo mengharuskan controller hanya bertindak sebagai adapter HTTP (autentikasi, parsing payload, dan formatting respon JSON), sedangkan seluruh manipulasi data, validasi bisnis, dan workflow ORM wajib berada di layer model (`stock.picking`).
- **Alternatives Considered:** Melakukan query pembuatan `stock.picking` dan `stock.move` langsung di dalam body fungsi controller. Alternatif ini ditolak keras karena melanggar pola *Fat Model, Skinny Controller* dan mempersulit pengujian unit test independen.
- **Consequences:** Logika pembuatan dokumen Delivery Order dapat diuji dan dipanggil kembali (*reusable*) dari konteks lain (misal cron job, testing, atau CLI shell).

### 3. Jaminan Idempotensi Transaksi Berdasarkan `sap_doc_number` dan Tipe `outgoing`
- **Rationale:** Pada arsitektur terdistribusi Two-Tier ERP, latensi jaringan atau kegagalan koneksi sesaat dapat menyebabkan sistem SAP mengirimkan ulang payload yang sama (*retry*). Dengan mengecek keberadaan dokumen `outgoing` yang memiliki nomor SAP terkait, sistem mencegah penciptaan dokumen ganda yang dapat memicu alokasi dan reservasi stok ganda.
- **Alternatives Considered:** Melempar eksepsi error duplikasi saat request kedua tiba. Ditolak karena melempar error membuat sistem pengirim menganggap transaksi gagal, padahal dokumen sudah berhasil tersimpan.
- **Consequences:** Sistem memiliki ketahanan tinggi (*high resilience*) dan menjamin integritas reservasi stok fisik.

### 4. Resolusi Lokasi Sumber dan Tujuan Otomatis
- **Rationale:** Operasi Delivery Order kargo harus mengambil stok dari lokasi fisik gudang (`stock_location`) dan memindahkannya ke lokasi virtual pelanggan (`customer location`). Mengambil konfigurasi dari tipe operasi `outgoing` pada gudang default (`DCLOW`) memastikan pergerakan stok konsisten dengan kaidah double-entry bookkeeping Odoo.
- **Alternatives Considered:** Melakukan hardcode pada nama atau ID lokasi. Ditolak karena melanggar aturan anti-hardcode proyek.
- **Consequences:** Kode bersifat dinamis dan mendukung skalabilitas multi-lokasi gudang.

## Technical Architecture & Data Schema

### 1. Kontrak REST API
- **Endpoint:** `POST /api/sap/outbound/delivery`
- **Header:**
  ```http
  Content-Type: application/json
  Authorization: Bearer <sap_api_token>
  ```
- **Payload Request:**
  ```json
  {
    "sap_doc_number": "SO-DELIV-2026-901",
    "customer_code": "CUST-ALFAMART-01",
    "destination_city": "Jakarta Barat",
    "items": [
      {
        "sap_material_code": "MAT-KOPI-01",
        "qty": 50.0,
        "uom": "Box"
      }
    ]
  }
  ```
- **Payload Response Sukses (HTTP 200):**
  ```json
  {
    "status": "SUCCESS",
    "code": 200,
    "message": "Delivery Order created successfully",
    "picking_id": 142,
    "picking_name": "DCLOW/OUT/00025",
    "sap_doc_number": "SO-DELIV-2026-901",
    "sync_ref": "SYNC-SO-20261026-9A1B2C"
  }
  ```

### 2. Implementasi ORM Model `stock.picking`
```python
@api.model
def create_outbound_from_sap(self, payload_dict):
    """Creates an outgoing stock picking (Delivery Order) and stock moves from SAP DO payload."""
    # 1. Validasi input mandatori
    # 2. Pengecekan idempoten
    # 3. Pencarian customer berdasarkan sap_partner_code
    # 4. Resolusi picking_type outgoing gudang DCLOW
    # 5. Pembuatan picking & stock.move untuk setiap item
    # 6. action_confirm() & action_assign()
    # 7. Return (picking_record, is_created)
```

## Risks & Trade-offs
| Risiko / Tantangan | Tingkat Keparahan | Strategi Mitigasi |
|---|---|---|
| Stok barang di gudang belum mencukupi saat Delivery Order diterima dari SAP. | Medium | Odoo ORM menangani kondisi ini secara anggun: `action_assign()` akan mereservasi stok parsial yang ada dan menandai status dokumen sebagai `confirmed` (Waiting Another Operation / Waiting Availability) tanpa menggagalkan transaksi API. |
| Customer SAP belum tersinkronisasi ke Odoo sebelum instruksi pengiriman tiba. | Low | Validasi menangkap ketiadaan partner dan mengembalikan HTTP 400 berisi pesan spesifik agar sinkronisasi master partner dijalankan terlebih dahulu. |
| Pengiriman ganda payload yang sama secara bersamaan (*concurrency race condition*). | Low | Pengecekan idempoten dilakukan pada awal transaksi sebelum pembuatan record picking. |

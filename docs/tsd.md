# Technical & System Design (TSD) — WMS Logistics SAP Connector

## 1. Arsitektur Sistem (Two-Tier Architecture)

```
[ Upper Line : SAP ]
  │
  │ REST API (JSON) / Webhook
  ▼
[ Integration Layer : Odoo Controller ]
  │
  ▼
[ Bottom Line : Odoo 17 Core Modules (stock, delivery) + Custom WMS ]
  │
  ▼
[ Operator Lapangan : Barcode Scanner, Tablet, Mobile Driver ]
```

## 2. Model & Tabel Kunci

### 2.1 Ekstensi Model Odoo Standard
1. **`product.template`**
   - `sap_material_code` (Char, Index): ID unik material di SAP.
   - `weight` & `volume` (Float): Kalkulasi kapasitas muatan armada.
2. **`res.partner`**
   - `sap_partner_code` (Char, Index): ID Customer atau Vendor di SAP.
3. **`stock.location`**
   - `sap_plant_code` (Char): Kode Plant SAP.
   - `sap_sloc_code` (Char): Storage Location SAP.
   - `barcode` (Char): Barcode pada rak fisik.
4. **`stock.picking`**
   - `sap_doc_number` (Char): Nomor referensi dokumen SAP (PO / Sales Order).
   - `sap_sync_status` (Selection: 'draft', 'pending', 'synced', 'failed').
   - `driver_id` (Many2one -> `res.partner` / supir).
   - `license_plate` (Char).
   - `proof_of_delivery` (Binary / Image tanda tangan penerima).

### 2.2 Model Baru (Custom)
1. **`sap.sync.log`**
   - `sync_type`: Master / Inbound / Outbound
   - `direction`: IN / OUT
   - `payload`: Text JSON
   - `status`: success / failed / pending
   - `error_message`: Text

## 3. Protokol & Kontrak API

- Format Payload: JSON
- Autentikasi: Token-based / Odoo API Key
- Idempotency: Menggunakan `sap_doc_number` dan `sap_material_code` sebagai kunci unik agar data tidak duplikat jika terjadi pengiriman ulang (*retry*).

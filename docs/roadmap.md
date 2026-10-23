# Odoo WMS & Logistics Execution

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| **Document ID**    | ODOO-WMS-SAP-01                               |
| **Version**        | 1.0                                           |
| **Status**         | Active                                        |
| **Effective Date** | 2026-10-23                                    |
| **Authors**        | Gilang Khrismahaq                             |

**Tujuan Dokumen:**
Dokumen ini memecah kebutuhan sistem WMS & Logistik terintegrasi SAP (Spesifikasi: `tsd.md`) secara menyeluruh (A–Z) ke dalam unit *capabilities* dan *changes* yang dapat dieksekusi secara independen menggunakan kerangka kerja OpenSpec. Setiap *change* merujuk langsung ke Spesifikasi Sistem (SSOT).

---

## Fase 1: Inisialisasi Ekosistem & Modul Inti (Foundation)

### 1.1 Capability: `module-scaffolding`
Pembuatan struktur dasar modul custom Odoo dan pendaftaran dependensi inti sistem inventori.

| Nama Change | Domain | Deskripsi | Referensi SSOT |
|---|---|---|---|
| `init-wms-connector-module` | Backend | Inisialisasi direktori `wms_sap_connector`, file `__init__.py`, dan file manifest `__manifest__.py`. Deklarasikan dependensi wajib (`stock`, `delivery`) agar Odoo menarik modul tersebut secara otomatis saat instalasi. | [tsd.md](tsd.md) (Bagian 3.1) |

### 1.2 Capability: `integration-audit-log`
Penyediaan infrastruktur pencatatan rekaman audit transaksi pertukaran data dua arah antara SAP dan Odoo.

| Nama Change | Domain | Deskripsi | Referensi SSOT |
|---|---|---|---|
| `create-sync-log-model` | Backend | Pembuatan model baru `sap.sync.log` beserta bidang data (`name`, `sync_type`, `direction`, `payload`, `status`, `error_message`, `sync_date`). | [tsd.md](tsd.md) (Bagian 3.2) |
| `setup-wms-security-groups` | Security | Konfigurasi `security/ir.model.access.csv` dan `security/security.xml` untuk peran Pengguna Gudang, Staf Logistik, dan Manajer Gudang. | [tsd.md](tsd.md) (Bagian 3.6) |
| `ui-backend-sync-log-views` | UI | Pembuatan tampilan Tree dan Form untuk model `sap.sync.log`, serta penyematan menu navigasi "SAP Integration Logs" di bawah modul Inventory. | [tsd.md](tsd.md) (Bagian 3.2) |

---

## Fase 2: Perluasan Master Data & Sinkronisasi (Master Data)

### 2.1 Capability: `master-data-models`
Perluasan model data standar Odoo untuk menampung atribut kode referensi SAP dan spesifikasi kargo.

| Nama Change | Domain | Deskripsi | Referensi SSOT |
|---|---|---|---|
| `extend-product-material-model` | Backend | Modifikasi model `product.template` dengan penambahan bidang `sap_material_code`, `weight`, dan `volume`, serta memproyeksikannya bersama widget gambar produk bawaan (`image_1920`) ke tampilan Form Produk untuk verifikasi visual staf gudang. | [tsd.md](tsd.md) (Bagian 3.2) |
| `extend-partner-customer-vendor` | Backend | Modifikasi model `res.partner` dengan penambahan bidang `sap_partner_code` untuk identifikasi unik entitas Vendor dan Customer dari SAP. | [tsd.md](tsd.md) (Bagian 3.2) |
| `extend-warehouse-location-model` | Backend | Modifikasi model `stock.location` dengan penambahan bidang `sap_plant_code`, `sap_sloc_code`, dan `barcode` lokasi rak fisik. | [tsd.md](tsd.md) (Bagian 3.2) |

### 2.2 Capability: `master-data-api-connector`
Penyediaan antarmuka REST API untuk menerima instruksi sinkronisasi data master dari SAP.

| Nama Change | Domain | Deskripsi | Referensi SSOT |
|---|---|---|---|
| `api-receive-sap-master-data` | Integrasi | Pembuatan Odoo Controller `/api/sap/master` bertipe JSON untuk menerima pembaruan data Material (termasuk konversi string gambar Base64 ke `image_1920`), Partner, dan Plant, lengkap dengan pencatatan otomatis ke `sap.sync.log`. | [tsd.md](tsd.md) (Bagian 3.5) |

---

## Fase 3: Alur Barang Masuk & Penempatan Rak (Inbound & Putaway)

### 3.1 Capability: `inbound-goods-receipt`
Otomatisasi pembuatan dan pemrosesan dokumen penerimaan barang pesanan pembelian (*Purchase Order*).

| Nama Change | Domain | Deskripsi | Referensi SSOT |
|---|---|---|---|
| `extend-picking-inbound-fields` | Backend | Penambahan bidang `sap_doc_number` dan `sap_sync_status` pada model `stock.picking`. | [tsd.md](tsd.md) (Bagian 3.2) |
| `api-receive-sap-purchase-order` | Integrasi | Pembuatan Odoo Controller `/api/sap/inbound/po` untuk memproses payload pesanan pembelian dari SAP menjadi dokumen *Stock Receipt* (`incoming`). | [tsd.md](tsd.md) (Bagian 2.2) |
| `automate-putaway-bin-allocation` | Backend | Penerapan alur penempatan otomatis (*Putaway Rule*) saat dokumen receipt divalidasi ke lokasi rak yang telah dipetakan. | [tsd.md](tsd.md) (Bagian 2.2) |

### 3.2 Capability: `inbound-sap-webhook`
Mekanisme pengiriman sinyal konfirmasi penerimaan fisik barang kembali ke sistem SAP.

| Nama Change | Domain | Deskripsi | Referensi SSOT |
|---|---|---|---|
| `webhook-notify-sap-goods-receipt` | Integrasi | Memicu transmisi webhook HTTP POST ke SAP sesaat setelah dokumen *Stock Receipt* divalidasi berstatus *Done* (*Goods Receipt Post*). | [tsd.md](tsd.md) (Bagian 3.4) |

---

## Fase 4: Alur Pengantaran, Armada & Bukti Serah Terima (Outbound & Delivery)

### 4.1 Capability: `fleet-management-models`
Penyediaan entitas pengelolaan armada kendaraan dan ketersediaan supir pengantar.

| Nama Change | Domain | Deskripsi | Referensi SSOT |
|---|---|---|---|
| `create-wms-vehicle-model` | Backend | Pembuatan model baru `wms.vehicle` beserta atribut (`license_plate`, `driver_id`, `max_weight`, `max_volume`, `state`). | [tsd.md](tsd.md) (Bagian 3.2) |
| `ui-backend-vehicle-views` | UI | Pembuatan antarmuka Tree dan Form untuk entitas armada serta menu manajemen armada di bawah sub-menu Logistik. | [tsd.md](tsd.md) (Bagian 3.2) |

### 4.2 Capability: `outbound-dispatch-surat-jalan`
Pemrosesan pesanan penjualan, pengelompokan muatan, dan penerbitan dokumen resmi pengantaran.

| Nama Change | Domain | Deskripsi | Referensi SSOT |
|---|---|---|---|
| `api-receive-sap-delivery-order` | Integrasi | Pembuatan Odoo Controller `/api/sap/outbound/delivery` untuk mengonversi instruksi pengiriman SAP menjadi dokumen *Delivery Order* (`outgoing`). | [tsd.md](tsd.md) (Bagian 2.2) |
| `extend-picking-dispatch-fields` | Backend | Menghubungkan relasi `vehicle_id` dan `driver_id` ke dokumen `stock.picking` serta menghitung total muatan berat/volume. | [tsd.md](tsd.md) (Bagian 3.2) |
| `report-official-surat-jalan` | UI | Desain laporan cetak QWeb PDF untuk dokumen resmi Surat Jalan Pengantaran Barang dilengkapi barcode nomor referensi. | [tsd.md](tsd.md) (Bagian 1.3) |

### 4.3 Capability: `proof-of-delivery-pod`
Pencatatan bukti penyerahan barang di lokasi pelanggan secara digital.

| Nama Change | Domain | Deskripsi | Referensi SSOT |
|---|---|---|---|
| `feature-driver-proof-of-delivery` | Backend | Penambahan antarmuka unggah foto/tanda tangan digital penerima (`proof_of_delivery`, `pod_signed_by`, `pod_timestamp`) pada dokumen pengantaran. | [tsd.md](tsd.md) (Bagian 3.2) |
| `webhook-notify-sap-goods-issue` | Integrasi | Memicu transmisi webhook notifikasi *Goods Issue (GI)* ke SAP setelah Surat Jalan divalidasi dan bukti POD terverifikasi lengkap. | [tsd.md](tsd.md) (Bagian 3.4) |

---

## Fase 5: Simulator SAP & Pengujian End-to-End (Simulation & Verification)

### 5.1 Capability: `mock-sap-service`
Penyediaan server tiruan untuk mereplikasi perilaku SAP dalam lingkungan pengembangan lokal.

| Nama Change | Domain | Deskripsi | Referensi SSOT |
|---|---|---|---|
| `setup-mock-sap-service` | Integrasi | Pembuatan skrip Python mandiri berbasis FastAPI/Flask (`mock_sap_server.py`) yang mampu menembakkan payload PO/Delivery dan menampung webhook Odoo. | [tsd.md](tsd.md) (Bagian 1.1) |
| `e2e-integration-validation` | QA | Eksekusi skenario uji menyeluruh mulai dari sinkronisasi master data, bongkar muat inbound, alokasi rak, pengiriman armada, hingga verifikasi POD. | [tsd.md](tsd.md) (Bagian 2.2) |

# Roadmap — WMS Logistics SAP Connector

Dokumen ini memetakan tahapan pengembangan modul Odoo 17 WMS & Logistik yang terintegrasi dengan SAP Upper Line.

---

## Milestone Overview

### Phase 1: Foundation & Master Data Synchronization
- Setup custom module `wms_sap_connector`.
- Ekstensi model master: Produk (`product.template`), Mitra (`res.partner`), Lokasi Rak (`stock.location`).
- Model tabel audit log: `sap.sync.log`.
- REST API endpoint untuk menerima sinkronisasi master data dari SAP.

### Phase 2: Inbound WMS & Putaway (Barang Masuk)
- Penerimaan PO Release dari SAP via webhook/API.
- Otomasi pembuatan dokumen *Receipt* di Odoo.
- Mekanisme validasi docking dan alokasi rak fisik (*Putaway Rule*).
- Kirim notifikasi status *Goods Receipt (GR)* balik ke SAP.

### Phase 3: Outbound Picking, Packing, & Delivery (Logistik Pengantaran)
- Penerimaan Delivery Order Request dari SAP.
- Alur *Picking* dari lokasi rak dan *Packing* kardus/label.
- Manajemen armada (`fleet_vehicle`) dan penugasan supir.
- Dokumen Surat Jalan Resmi dan Proof of Delivery (POD).
- Kirim konfirmasi *Goods Issue (GI)* ke SAP.

### Phase 4: Mock SAP Server & Integration Testing
- Mini-service simulator SAP (Python) untuk mendemokan pertukaran data dua arah.
- End-to-end testing skenario Inbound & Outbound.

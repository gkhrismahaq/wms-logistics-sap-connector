# WMS Logistics SAP Connector (Odoo 17)

Sistem eksekusi pergudangan (*Warehouse Management System*) dan logistik pengantaran berbasis **Odoo 17** yang terintegrasi dengan **SAP** (Upper Line) menggunakan pendekatan arsitektur *Two-Tier ERP*.

---

## 🚀 Quick Start

### 1. Menjalankan Container
Pastikan Docker Desktop sudah aktif, lalu jalankan:
```bash
make start
```
* Odoo Web UI: [http://localhost:8070](http://localhost:8070)
* PostgreSQL Port: Internal Docker network (`wms-network`)

### 2. Monitoring Log
```bash
make logs odoo    # Stream log container Odoo
make logs db      # Stream log container Database
```

### 3. Perintah Makefile Lainnya
```bash
make stop         # Menghentikan container
make restart      # Me-restart container
make console      # Masuk ke Odoo interactive shell
make psql         # Masuk ke PostgreSQL terminal
make addon <nama> # Restart & upgrade modul custom spesifik
```

---

## 📂 Struktur Project

```
wms-logistics-sap-connector/
├── .agent/              # Skill & Workflow Antigravity (OpenSpec)
├── addons/              # Folder custom modules Odoo
├── docs/                # Blueprint arsitektur (TSD & Roadmap)
├── etc/odoo/            # Konfigurasi odoo.conf
├── openspec/            # Perubahan spesifikasi & task OpenSpec
├── docker-compose.yaml  # Docker service definition (Port 8070)
├── Makefile             # Automation shortcut commands
└── README.md
```

---

## 📖 Metodologi
Project ini dikembangkan menggunakan metodologi **Spec-Driven Development** via **OpenSpec**. Setiap penambahan fitur bisnis diawali dengan proposal, spesifikasi fungsional, dan *task list* sebelum implementasi kode.

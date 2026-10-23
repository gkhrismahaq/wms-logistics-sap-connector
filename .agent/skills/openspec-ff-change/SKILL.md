---
name: openspec-ff-change
description: Fast-forward through OpenSpec artifact creation. Use when the user wants to quickly create all artifacts needed for implementation without stepping through each one individually.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.7.0"
---

# Fast Forward Change
`/openspec-ff-change <artifact> <change>`

## [CRITICAL SYSTEM INSTRUCTIONS: STRICT COMPLIANCE REQUIRED]
Kerjakan tugas ini dengan ketelitian absolut (zero hallucination, zero assumption). Anda diwajibkan mengeksekusi operasi ini berdasarkan pedoman berikut tanpa melakukan manuver di luar konteks:
1. Terapkan secara mutlak aturan pada `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/openspec/config.yaml`
2. Jadikan `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/roadmap.md` sebagai landasan untuk setiap change dan capability (capability akan menjadi nama spec) yang sedang dikerjakan.
3. Tinjau kembali arsitektur dan file proyek yang ada saat ini. Pastikan pengembangan berjalan konsisten, tidak ada duplikasi, dan tidak ada resource yang terabaikan.
4. Jadikan semua dokumen relevan di `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/tsd.md` sebagai Single Source of Truth (SSOT).
5. Kepatuhan Arsitektur & Reusabilitas: Tinjau kembali arsitektur Clean Architecture serta file, modul, dan utilitas proyek yang sudah ada saat ini. Pastikan rancangan pengembangan berjalan konsisten, memanfaatkan kode relevan yang sudah tersedia, modular, tidak ada duplikasi (anti-redundansi), dan tidak ada resource yang terabaikan.

---

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `view`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Input Syntax**:
`/openspec-ff-change <artifact> <change>` or `/openspec-ff-change <change>`
- `<change>`: Nama change dalam format kebab-case (wajib divalidasi terhadap `docs/roadmap.md`).
- `<artifact>` (opsional): ID artifact tertentu yang ingin dibuat secara spesifik atau batas akhir pembuatan (`proposal`, `specs`, `design`, `tasks`). Jika diabaikan, seluruh artifact yang dibutuhkan untuk implementasi akan digenerate secara berurutan.

**Steps**

1. **Grounded Change & Capability Selection from Roadmap**

   - **DILARANG** melakukan open-ended guessing atau berasumsi di luar konteks proyek.
   - Buka dan telaah `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/roadmap.md`:
     - Jika `<change>` diberikan oleh pengguna: cari dan cocokkan `<change>` tersebut di `docs/roadmap.md` untuk mengetahui Fase, Domain, Deskripsi, Referensi SSOT di `docs/tsd.md`, serta **Capability induknya**. Nama capability ini **MUTLAK** menjadi nama spec (`specs/<capability-name>/spec.md`).
     - Jika `<change>` belum diberikan atau ambigu: buka `docs/roadmap.md`, tinjau change yang sudah ada di `openspec/changes/`, dan tentukan change berikutnya yang sesuai urutan fase pada roadmap. Konfirmasikan ke pengguna berdasarkan opsi konkret dari roadmap tersebut.

2. **Pre-Creation Review (Clean Architecture, SSOT & Existing Code)**

   Sebelum membuat file artifact apa pun:
   - Baca bagian terkait pada `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/tsd.md` (SSOT) untuk memahami kebutuhan bisnis, alur proses, dan spesifikasi teknis model/field/API.
   - Baca `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/openspec/config.yaml` untuk memastikan kepatuhan penuh terhadap format template, konvensi bahasa, dan batasan Odoo 17.
   - **Tinjau Arsitektur & Reusabilitas Kode**: Periksa direktori proyek dan modul (`addons/wms_sap_connector` dan file terkait) untuk:
     - Mengidentifikasi model, view, controller, atau utility yang sudah ada.
     - Memastikan rancangan konsisten dengan pola Odoo 17 & Clean Architecture.
     - Mencegah duplikasi field/fungsi/tampilan (anti-redundansi).
     - Memastikan tidak ada resource yang terabaikan atau menjadi yatim (orphan).

3. **Create the Change Directory**
   ```bash
   openspec new change "<name>"
   ```
   Jika direktori change sudah ada, lanjutkan proses pembuatan artifact yang belum selesai.

4. **Get the Artifact Build Order**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse JSON untuk mendapatkan:
   - `applyRequires`: daftar artifact yang dibutuhkan untuk fase implementasi (e.g., `["tasks"]`).
   - `artifacts`: daftar artifact beserta status (`ready`, `done`, `blocked`, `skipped`) dan dependency edges (`requires`).
   - `planningHome`, `changeRoot`, `artifactPaths`, dan `actionContext`.

   Tentukan target pembuatan artifact:
   - Jika pengguna menentukan `<artifact>` spesifik pada pemanggilan `/openspec-ff-change <artifact> <change>`, buat hingga artifact tersebut terpenuhi.
   - Jika `<artifact>` tidak ditentukan, buat seluruh artifact yang dibutuhkan secara transitif (`proposal` → `specs` → `design` → `tasks`).

5. **Generate Artifacts with Strict Compliance to config.yaml**

   Secara berurutan untuk setiap artifact yang berstatus `ready`:

   a. Dapatkan instruksi artifact:
      ```bash
      openspec instructions <artifact-id> --change "<name>" --json
      ```

   b. Buat file artifact dengan kepatuhan mutlak pada aturan `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/openspec/config.yaml`:
      - **Language Rule**: Semua judul markdown (headings) **WAJIB** menggunakan bahasa Inggris (`# Proposal: ...`, `## Why`, `## What Changes`, dll). Semua penjelasan/isi tubuh (body explanations) **WAJIB** menggunakan bahasa Indonesia formal.
      - **Code Naming**: Nama model Odoo, field, dan file path **WAJIB** dibungkus backticks (contoh: `stock.picking`, `sap.sync.log`, `addons/wms_sap_connector/...`).

      - **Artifact: `proposal.md`**:
        - Wajib mencantumkan tabel metadata: Change Name, Roadmap Phase, Target Cap., Est. Effort, Risk Level.
        - Wajib memiliki bagian:
          - `## Why`: Penjelasan masalah bisnis/teknis dengan kutipan referensi ke `docs/tsd.md` (Bagian X.Y) dan `docs/roadmap.md` (Fase X.Y).
          - `## What Changes`: Rincian domain Backend (ORM & Models), Security & Access Rights, Views & UI, Integration & API.
          - `## Capabilities`: New Capabilities (`{capability-name}` dari roadmap), Modified Capabilities, Removed Capabilities.
          - `## Impact & Scope`: Files to Create, Files to Modify, SSOT Documents Referenced, Estimated Effort, Complexity & Risk Analysis.

      - **Artifact: `specs/<capability-name>/spec.md`**:
        - Target path **MUTLAK**: `specs/{capability-name}/spec.md` di mana `{capability-name}` diambil langsung dari capability di `docs/roadmap.md`.
        - Wajib mengikuti format OpenSpec Delta Specs:
          - `## Purpose`: Penjelasan fungsi kapabilitas bagi operasional WMS / integrasi SAP.
          - `## ADDED Requirements`: Requirement berformat `### Requirement: [REQ-{CAP}-{01}] {Nama Requirement}`, menggunakan RFC 2119 keywords (`MUST`, `MUST NOT`, `SHOULD`, `MAY`), referensi ke `docs/tsd.md` (Bagian X.Y), serta skenario konkret `#### Scenario: {Happy Path}` dan `#### Scenario: {Edge Case}` dengan klausa `GIVEN / WHEN / THEN`.
          - `## MODIFIED Requirements` & `## REMOVED Requirements`.

      - **Artifact: `design.md`**:
        - Wajib mengikuti format Architecture Decision Record (ADR):
          - Metadata: Change Name, Arch Pattern, Primary Models.
          - `## Context`: Latar belakang teknis dan batasan saat ini.
          - `## Goals / Non-Goals`: Sasaran terukur dan batasan non-goals agar tidak terjadi scope creep.
          - `## Decisions (ADR)`: Rationale, Alternatives Considered, Consequences.
          - `## Technical Architecture & Data Schema`: Potongan kode deklarasi model/field Python Odoo, inheritance, views XML structure, atau skema JSON API.
          - `## Risks & Trade-offs`: Tabel risiko, tingkat keparahan, dan mitigasi.

      - **Artifact: `tasks.md`**:
        - Wajib mengikuti format item task: `- [ ] {Number}.{Sub} [{Domain}] {Action-oriented description}`.
        - Domain tag **WAJIB** salah satu dari: `[Backend]`, `[Security]`, `[UI]`, `[Integration]`, `[Test]`.
        - Target file path **WAJIB** dicantumkan spesifik dalam backticks (`addons/wms_sap_connector/...`).
        - Durasi per task **TIDAK BOLEH** melebihi 2 jam.
        - Wajib mengikuti urutan 5 fase implementasi secara runtut:
          1. Data Model & Backend Foundation
          2. Security & Access Control
          3. User Interface & Views
          4. Business Logic & Integration Endpoints
          5. Verification & Testing (termasuk verifikasi upgrade via `make addon wms_sap_connector` dan pengujian skenario spec.md).

   c. Verifikasi keberadaan file fisik artifact setelah penulisan sebelum melanjutkan ke artifact berikutnya.
   d. Jalankan kembali `openspec status --change "<name>" --json` untuk memperbarui status artifact selanjutnya.
   e. Tampilkan progres singkat: "✓ Created <artifact-id>".

6. **Show Final Status**
   ```bash
   openspec status --change "<name>"
   ```

**Output**

Setelah semua artifact target berhasil dibuat:
- Rangkuman Change Name, Roadmap Phase, dan Target Capability.
- Daftar artifact yang berhasil dibuat berserta path filenya.
- Konfirmasi kesiapan: "All artifacts needed for implementation are ready and strictly compliant with project standards."
- Prompt lanjutan: "Jalankan `/openspec-apply-change <change>` untuk memulai implementasi kode."

**Guardrails**
- **Zero Hallucination & Zero Assumption**: Jangan pernah mengarang model, field, endpoint, atau alur yang tidak tercantum dalam `docs/tsd.md` (SSOT) dan `docs/roadmap.md`.
- **Roadmap-Grounded**: Setiap change dan capability wajib terikat pada `docs/roadmap.md`.
- **Absolute Template Adherence**: Patuhi 100% struktur dan konvensi penamaan dalam `openspec/config.yaml`.
- **Clean Architecture & Anti-Redundancy**: Selalu telaah kode eksisting sebelum merancang artifact baru agar tidak terjadi tumpang tindih.
- Verifikasi setiap artifact fisik tersimpan di disk sebelum melanjutkan ke artifact berikutnya.

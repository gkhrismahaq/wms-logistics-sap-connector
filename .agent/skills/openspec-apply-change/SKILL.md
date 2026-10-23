---
name: openspec-apply-change
description: Implement tasks from an OpenSpec change. Use when the user wants to start implementing, continue implementation, or work through tasks.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.7.0"
---

# Apply Change
`/openspec-apply-change <change>`

## [CRITICAL SYSTEM INSTRUCTIONS: HIGH-QUALITY EXECUTION REQUIRED]
Lakukan penerapan perubahan (apply change) dengan kepatuhan penuh (zero hallucination, zero assumption) dan ketelitian tingkat tinggi. Hasil akhir tidak boleh sekadar "kode tambalan". Kode wajib berstandar production-ready, mengimplementasikan arsitektur enterprise-level, mencerminkan best practice professional developer, serta bersih dari spaghetti code maupun nilai hardcoded.
DILARANG TELEDOR! Anda WAJIB mematuhi panduan operasional berikut:
1. Perlindungan Kode Eksisting (Non-Destructive Execution): Anda DILARANG KERAS menimpa, menghapus, atau merusak kode eksisting yang sudah berfungsi dengan benar dan tidak memiliki kesalahan, kecuali secara eksplisit diperlukan oleh ruang lingkup perubahan (change). Lakukan modifikasi dengan presisi bedah, bukan perombakan membabi buta.
2. Jadikan `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/openspec/config.yaml` sebagai aturan mutlak penulisan format.
3. Gunakan semua dokumen relevan di `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/tsd.md` sebagai referensi mutlak (SSOT).
4. Tinjau ulang file dan direktori proyek sebelum menulis kode untuk mencegah redundansi, mengenali ketergantungan kode yang sudah ada, dan memastikan tidak ada konteks arsitektur yang dilanggar.
5. Zero Problems & Pre-Completion Scan: DILARANG KERAS meninggalkan problems dalam bentuk apa pun (termasuk syntax error, type error, unused variables, unused imports, dead code, atau warnings). Sebelum menyatakan task selesai, Anda WAJIB melakukan scanning dan validasi menyeluruh pada seluruh kode yang dimodifikasi untuk memastikan implementasi berjalan bersih, solid, dan tanpa sisa isu teknis.

---

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `view`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Input**: Specify a change name (`/openspec-apply-change <change>`). If omitted, infer from conversation context or active changes in `openspec/changes/`. If ambiguous, prompt the user with active changes from `openspec list --json`.

**Steps**

1. **Select and Validate the Change**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change.
   - Auto-select if only one active change exists.
   - If ambiguous, run `openspec list --json` to get available changes and ask the user to select one.

   Always announce: "Using change: <name>" and how to override (e.g., `/openspec-apply-change <other>`).

2. **Check Status and Prerequisites**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse JSON to verify:
   - `isComplete`: Are planning artifacts created and ready?
   - `schemaName`: Workflow being used (e.g., "spec-driven").
   - `planningHome`, `changeRoot`, and `actionContext`.
   - If artifacts are missing or blocked, prompt user to complete artifacts via `/openspec-ff-change <name>`.

3. **Get Apply Instructions**
   ```bash
   openspec instructions apply --change "<name>" --json
   ```
   Parse JSON to extract:
   - `contextFiles`: concrete paths to planning artifacts (`proposal.md`, `specs/.../spec.md`, `design.md`, `tasks.md`).
   - `tasks`: list of implementation tasks and current completion status.
   - `dynamicInstruction`: guidance based on state.

4. **Load Planning Context, SSOT, and Technical Standards**

   Sebelum menulis baris kode apa pun, Anda **WAJIB** membaca dan memahami:
   - **Context Files**: Baca seluruh file yang terdaftar di `contextFiles` (`proposal.md`, `specs/.../spec.md`, `design.md`, `tasks.md`).
   - **SSOT**: Baca dokumen relevan di `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/tsd.md` (SSOT) untuk validasi logika bisnis, skema integrasi, dan aturan model.
   - **Project Standards**: Tinjau `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/openspec/config.yaml` (`Hard Technical Constraints` & `operations.apply.guidance`).

5. **Display Current Progress**

   Tampilkan status awal:
   - Change yang sedang dikerjakan.
   - Progress: "N/M tasks complete".
   - Task berikutnya yang akan dieksekusi.

6. **Implement Tasks Sequentially (Strict Quality & Non-Destructive Loop)**

   Eksekusi setiap task yang tertunda (`- [ ]`) pada file `tasks.md` secara berurutan (sequential order: 1.1 → 1.2 → 2.1 ...). Untuk setiap task:

   a. **Pre-Implementation Architectural Review (Rule 4)**:
      - Tinjau ulang file dan direktori proyek sebelum menulis kode.
      - Kenali ketergantungan kode yang sudah ada (models, views, security groups, utilities).
      - Cegah redundansi: jangan membuat ulang helper, model, atau fungsi yang sudah tersedia.
      - Pastikan tidak ada konteks arsitektur (Odoo 17 Clean Architecture) yang dilanggar.

   b. **Non-Destructive Surgical Implementation (Rule 1, Rule 2, Rule 3)**:
      - **Perlindungan Kode Eksisting (Non-Destructive Execution)**: Anda DILARANG KERAS menimpa, menghapus, atau merusak kode eksisting yang sudah berfungsi dengan benar dan tidak memiliki kesalahan, kecuali secara eksplisit diperlukan oleh ruang lingkup perubahan (change). Lakukan modifikasi dengan presisi bedah, bukan perombakan membabi buta.
      - **Production-Ready & Enterprise Quality**:
        - Hasil akhir tidak boleh sekadar "kode tambalan". Kode wajib berstandar production-ready, mengimplementasikan arsitektur enterprise-level, mencerminkan best practice professional developer, serta bersih dari spaghetti code maupun nilai hardcoded.
        - Terapkan standar Odoo 17 enterprise (ORM methods yang aman, `api.depends`, `api.constrains`, inheritance `_inherit`, domain filters, XML ID naming convention, logging transaksi via `sap.sync.log`).
        - BERSIH dari nilai hardcoded: gunakan constants, konfigurasi `res.config.settings`, atau parameter model.
        - Pertahankan seluruh docstrings, komentar, dan konvensi penamaan kode yang relevan.

   c. **Zero Problems & Pre-Completion Scan (Rule 5)**:
      - DILARANG KERAS meninggalkan problems dalam bentuk apa pun (termasuk syntax error, type error, unused variables, unused imports, dead code, atau warnings).
      - Sebelum menyatakan task selesai, Anda WAJIB melakukan scanning dan validasi menyeluruh pada seluruh kode yang dimodifikasi untuk memastikan implementasi berjalan bersih, solid, dan tanpa sisa isu teknis:
        - **Python Compilation & Syntax Check**: Jalankan pengujian sintaks Python pada file yang diubah (misalnya via `python3 -m py_compile <path>` atau linter).
        - **XML Validation**: Pastikan file XML views / data terstruktur valid, tag tertutup rapi, dan ID record konsisten.
        - **Code Hygiene**: Pastikan tidak ada unused imports, variable tidak terpakai, atau dead code yang tersisa.
        - **Module / Integration Verification**: Jalankan verifikasi modul (misalnya upgrade via `make addon wms_sap_connector` atau automated test terkait) dan pastikan output bersih tanpa error atau peringatan kritis.
      - **HANYA setelah scanning dan validasi terbukti bersih 100% tanpa sisa isu teknis**:
        - Update status checkbox task pada file `tasks.md`: ubah `- [ ]` menjadi `- [x]`.

   d. **Pause & Ask If**:
      - Terjadi keambiguan kritis pada kebutuhan bisnis → minta klarifikasi kepada pengguna.
      - Implementasi mengungkap cacat desain pada artifact sebelumnya → sarankan pembaruan artifact terlebih dahulu.
      - Ditemukan blocker teknis di luar ruang lingkup perubahan.

7. **Show Final Status Upon Completion**

   Setelah seluruh task selesai:
   - Tampilkan daftar task yang berhasil diselesaikan (`- [x]`).
   - Laporkan hasil Pre-Completion Scan yang membuktikan implementasi bersih (0 problems, 0 syntax/type errors, 0 unused imports, clean architecture).
   - Sarankan verifikasi akhir atau pengarsipan change via `/openspec-verify-change` atau `/openspec-archive-change`.

**Output During Implementation**

```markdown
## Implementing: <change-name> (schema: <schema-name>)

Working on task 1.1: [Backend] {Deskripsi task}
- Pre-implementation review: checked existing models & architecture
- Applying surgical non-destructive changes...
- Pre-completion scan: Python syntax verified, zero unused imports/variables, zero problems
✓ Task 1.1 complete: `- [x]` updated

Working on task 1.2: ...
```

**Guardrails**
- **Non-Destructive Execution**: Jangan pernah merusak kode eksisting yang berfungsi normal.
- **Enterprise Standards**: Tidak ada tambalan, tidak ada spaghetti code, tidak ada nilai hardcoded.
- **Strict Format & SSOT**: Selalu jadikan `config.yaml` sebagai acuan format dan `docs/tsd.md` sebagai referensi mutlak.
- **Zero Problems Policy**: Wajib lulus scanning menyeluruh sebelum mencentang task selesai.
- **Sequential Task Execution**: Kerjakan task secara berurutan sesuai fase di `tasks.md`.

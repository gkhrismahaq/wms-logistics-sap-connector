---
name: openspec-continue-change
description: Continue working on an OpenSpec change by creating the next artifact. Use when the user wants to progress their change, create the next artifact, or continue their workflow.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.7.0"
---

# Continue Change
`/openspec-continue-change [change]`

## [CRITICAL SYSTEM INSTRUCTIONS: STRICT COMPLIANCE REQUIRED]
Kerjakan tugas ini dengan ketelitian absolut (zero hallucination, zero assumption). Anda diwajibkan mengeksekusi operasi ini berdasarkan pedoman berikut tanpa melakukan manuver di luar konteks:
1. Terapkan secara mutlak aturan pada `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/openspec/config.yaml`
2. Jadikan `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/roadmap.md` sebagai landasan untuk setiap change dan capability (capability akan menjadi nama spec) yang sedang dikerjakan.
3. Tinjau kembali arsitektur dan file proyek yang ada saat ini. Pastikan pengembangan berjalan konsisten, tidak ada duplikasi, dan tidak ada resource yang terabaikan.
4. Jadikan semua dokumen relevan di `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/tsd.md` sebagai Single Source of Truth (SSOT).
5. Kepatuhan Arsitektur & Reusabilitas: Tinjau kembali arsitektur Clean Architecture serta file, modul, dan utilitas proyek yang sudah ada saat ini. Pastikan rancangan pengembangan berjalan konsisten, memanfaatkan kode relevan yang sudah tersedia, modular, tidak ada duplikasi (anti-redundansi), dan tidak ada resource yang terabaikan.

---

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `view`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Input**: Optionally specify a change name. If omitted, infer from conversation context or active changes in `openspec/changes/`. Ground change names against `docs/roadmap.md`.

**Steps**

1. **Select the Change (Grounded in Roadmap)**

   If a name is provided, verify it against `docs/roadmap.md`. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` and match against `docs/roadmap.md`

   Always announce: "Using change: <name>" and how to override (e.g., `/openspec-continue-change <other>`).

2. **Check Current Status**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse JSON to understand current state (`artifacts`, `isComplete`, `planningHome`, `changeRoot`).

3. **Act Based on Status**:

   **If all artifacts are complete (`isComplete: true`)**:
   - Tampilkan status lengkap.
   - Sarankan: "Semua artifact sudah siap! Jalankan `/openspec-apply-change <name>` untuk memulai implementasi kode."
   - STOP

   **If artifacts are ready to create**:
   - Pilih artifact PERTAMA dengan status `ready`.
   - Dapatkan instruksi:
     ```bash
     openspec instructions <artifact-id> --change "<name>" --json
     ```
   - **Tinjau Arsitektur & SSOT**:
     - Baca `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/tsd.md` (SSOT) dan `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/roadmap.md`.
     - Periksa file eksisting di `addons/wms_sap_connector` untuk memastikan Clean Architecture, modularitas, dan anti-redundansi.
   - **Buat File Artifact Sesuai Aturan Mutlak `openspec/config.yaml`**:
     - Judul dalam bahasa Inggris, isi dalam bahasa Indonesia.
     - Nama model, field, path dalam backticks.
     - Ikuti template `config.yaml` secara presisi (`proposal`, `specs/{capability}/spec.md`, `design.md`, `tasks.md`).
     - Simpan ke `resolvedOutputPath`.
   - STOP setelah membuat SATU artifact agar pengguna dapat meninjau secara bertahap jika diinginkan.

4. **Show Progress**
   ```bash
   openspec status --change "<name>"
   ```

**Guardrails**
- Zero hallucination, zero assumption.
- Strict template compliance with `openspec/config.yaml`.
- Grounded in `docs/roadmap.md` and `docs/tsd.md` (SSOT).

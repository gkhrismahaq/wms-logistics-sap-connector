---
name: openspec-propose
description: Propose a new change with all artifacts generated in one step. Use when the user wants to quickly describe what they want to build and get a complete proposal with design, specs, and tasks ready for implementation.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.7.0"
---

# Propose Change
`/openspec-propose [change]`

## [CRITICAL SYSTEM INSTRUCTIONS: STRICT COMPLIANCE REQUIRED]
Kerjakan tugas ini dengan ketelitian absolut (zero hallucination, zero assumption). Anda diwajibkan mengeksekusi operasi ini berdasarkan pedoman berikut tanpa melakukan manuver di luar konteks:
1. Terapkan secara mutlak aturan pada `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/openspec/config.yaml`
2. Jadikan `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/roadmap.md` sebagai landasan untuk setiap change dan capability (capability akan menjadi nama spec) yang sedang dikerjakan.
3. Tinjau kembali arsitektur dan file proyek yang ada saat ini. Pastikan pengembangan berjalan konsisten, tidak ada duplikasi, dan tidak ada resource yang terabaikan.
4. Jadikan semua dokumen relevan di `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/tsd.md` sebagai Single Source of Truth (SSOT).
5. Kepatuhan Arsitektur & Reusabilitas: Tinjau kembali arsitektur Clean Architecture serta file, modul, dan utilitas proyek yang sudah ada saat ini. Pastikan rancangan pengembangan berjalan konsisten, memanfaatkan kode relevan yang sudah tersedia, modular, tidak ada duplikasi (anti-redundansi), dan tidak ada resource yang terabaikan.

---

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `view`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Input**: Change name grounded in `docs/roadmap.md`. If omitted, select from `docs/roadmap.md`.

**Steps**

1. **Select and Verify Change from Roadmap**
   - Periksa `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/roadmap.md`.
   - Cocokkan change dengan capability induknya. Capability name **MUTLAK** menjadi nama spec (`specs/<capability-name>/spec.md`).

2. **Pre-Creation Review**
   - Pelajari spesifikasi di `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/tsd.md` (SSOT).
   - Tinjau aturan format di `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/openspec/config.yaml`.
   - Tinjau kode eksisting pada direktori proyek (`addons/wms_sap_connector`) untuk memastikan Clean Architecture, modularitas, dan anti-redundansi.

3. **Create Change Directory**
   ```bash
   openspec new change "<name>"
   ```

4. **Generate All Artifacts Sequentially**
   Ikuti siklus dependensi: `proposal` → `specs` → `design` → `tasks`.
   Setiap artifact dibuat dengan kepatuhan mutlak terhadap aturan template di `openspec/config.yaml`:
   - Headings in English, Body in formal Indonesian.
   - Odoo models, fields, and paths wrapped in backticks.
   - `proposal.md`: format tabel, Why (ref `tsd.md` & `roadmap.md`), What Changes, Capabilities, Impact & Scope.
   - `specs/<capability-name>/spec.md`: Delta Specs format, RFC 2119 keywords, Happy Path & Edge Case scenarios.
   - `design.md`: ADR format, Context, Goals/Non-Goals, Decisions, Technical Architecture & Data Schema, Risks table.
   - `tasks.md`: `- [ ] {Number}.{Sub} [{Domain}] {Description}`, domain tags, backticked file paths, max 2h per task, 5 phases.

5. **Show Final Status**
   ```bash
   openspec status --change "<name>"
   ```
   Prompt: "All artifacts created! Run `/openspec-apply-change <change>` to start implementation."

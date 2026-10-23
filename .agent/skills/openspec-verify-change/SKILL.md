---
name: openspec-verify-change
description: Verify implementation matches change artifacts. Use when the user wants to validate that implementation is complete, correct, and coherent before archiving.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.7.0"
---

# Verify Change
`/openspec-verify-change [change]`

## [CRITICAL SYSTEM INSTRUCTIONS: STRICT VERIFICATION REQUIRED]
Lakukan verifikasi perubahan (verify change) dengan kepatuhan penuh (zero hallucination, zero assumption) dan ketelitian tingkat tinggi:
1. Jadikan `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/openspec/config.yaml` sebagai aturan mutlak penulisan format dan standar Odoo 17.
2. Gunakan semua dokumen relevan di `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/tsd.md` sebagai Single Source of Truth (SSOT).
3. Verifikasi Perlindungan Kode Eksisting (Non-Destructive Execution): Pastikan tidak ada kode fungsional eksisting yang tertimpa, terhapus, atau rusak di luar ruang lingkup perubahan.
4. Zero Problems Verification: DILARANG KERAS meloloskan kode yang memiliki syntax error, type error, unused variables, unused imports, dead code, atau warnings.
5. Verifikasi Kepatuhan Arsitektur: Pastikan kode modular, mematuhi Clean Architecture Odoo 17, tidak ada redundansi, dan tidak ada resource yang terabaikan.

---

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `view`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context or active changes in `openspec/changes/`.

**Steps**

1. **Select the Change**
   If a name is provided, use it. Otherwise auto-select or prompt from `openspec list --json`.
   Always announce: "Verifying change: <name>".

2. **Check Status to Understand the Schema**
   ```bash
   openspec status --change "<name>" --json
   ```

3. **Get Planning Context and Load Artifacts**
   ```bash
   openspec instructions apply --change "<name>" --json
   ```
   Read all artifacts from `contextFiles` (`proposal.md`, `specs/...`, `design.md`, `tasks.md`), as well as `/Users/gilangkhrismahaq/Projects/wms-logistics-sap-connector/docs/tsd.md` (SSOT).

4. **Initialize Verification Report Structure**
   Create a report structure across four core dimensions:
   - **Completeness**: Task completion in `tasks.md` and requirement coverage.
   - **Correctness & SSOT Adherence**: Implementation fidelity to `docs/tsd.md` and spec scenarios.
   - **Zero Problems & Code Quality**: Syntax verification, unused imports/variables, dead code, warnings, and non-destructive execution.
   - **Coherence & Clean Architecture**: ADR decisions adherence, clean architecture, and modularity.

5. **Verify Completeness**
   - Parse `tasks.md`: Count complete (`- [x]`) vs incomplete (`- [ ]`).
   - If incomplete tasks exist: add CRITICAL issue.
   - Verify requirement coverage against `specs/<capability>/spec.md`.

6. **Verify Correctness & SSOT Alignment**
   - Check code against `docs/tsd.md` (SSOT) sections.
   - Assess scenarios (Happy Path, Edge Case) in `spec.md` to ensure proper handling.

7. **Verify Zero Problems & Non-Destructive Execution**
   - Perform Python syntax / compilation checks on modified files (`python3 -m py_compile <path>`).
   - Verify XML views and security files are well-formed and valid.
   - Check for unused imports, unused variables, and dead code.
   - Verify that existing functional code was NOT accidentally broken or overwritten.
   - If any problems exist: add CRITICAL issue.

8. **Verify Coherence & Architecture**
   - Adherence to decisions in `design.md` (ADR).
   - Odoo 17 conventions: security rules defined in `ir.model.access.csv` / `security.xml`, views registered in `__manifest__.py`, logging via `sap.sync.log`.

9. **Generate Verification Report**

```markdown
## Verification Report: <change-name>

### Summary
| Dimension                    | Status             |
|------------------------------|--------------------|
| Completeness                 | X/Y tasks complete |
| Correctness & SSOT           | M/N reqs covered   |
| Zero Problems & Code Quality | Passed / Issues    |
| Coherence & Architecture     | Clean / Issues     |

### Issues by Priority
1. **CRITICAL** (Must fix before archive):
   - Incomplete tasks
   - Syntax/type errors, unused imports, dead code, warnings
   - Unintended changes to existing functional code
2. **WARNING** (Should fix):
   - Spec/design divergences
3. **SUGGESTION**:
   - Minor improvements

### Final Assessment
- If CRITICAL: "X critical issue(s) found. Fix before archiving."
- If Clean: "All checks passed with Zero Problems. Ready for archive."
```

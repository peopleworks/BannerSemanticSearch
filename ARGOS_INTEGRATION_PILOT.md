# Argos Reports → BannerSemanticSearch Integration

**Status:** Pilot proposal, not started
**Owner:** Pedro
**Date:** 2026-04-17

---

## Why this exists

The `argos_tool` project at `C:\Proyecto\Waubonsee\argos_tool\` parses Evisions Argos exports into HTML documentation. There are **195 reports** in `argos_tool/ArgosDoc/`, each one a real production query HR/Payroll runs against Banner.

Each Argos report is effectively:

- **Title** = the business question being asked ("IDES Quarterly Wages")
- **SQL** = the answer that has been validated in production for years
- **Tables** = the Banner objects that actually carry the data

This is institutional knowledge that's currently invisible to BannerSemanticSearch. Surfacing it would let the SQL Explainer say: *"This query touches the same tables as 3 production Argos reports — here they are."*

Confirmed value: `IDES Quarterly Wages.html` line 285 already shows `WHERE PWVEARN.PWVEARN_POSN <> 'SE9000'` — the row-level fix we backed into on Apr 8 was sitting in this Argos report the whole time. Surfacing this earlier would have saved real diagnostic time.

---

## The risk to manage

**Quality varies.** Some Argos reports use deprecated patterns (e.g., older PERETOT + PWVEMPL EXISTS for SUI, or `PHRHIST_GROSS > 0` filters that double-count adjustments). Dumping all 195 reports as "business cases" would actively teach the SQL Explainer the bugs we just removed in `business_cases.txt` (BC015/BC026/BC028 — see commit `Apr 17 2026`).

We need **two tiers**:

| Tier | What | Curated? | Volume |
|---|---|---|---|
| Reference index | All 195 reports — title, tables, params, SQL, source filename | No | All |
| Curated cases | Selected reports promoted to `business_cases.txt` with manual notes | Yes | ~10–15 |

The reference index is mechanical and complete. The curated cases are teaching material with quality tags.

---

## Proposed file layout

```
BannerSemanticSearch/
├── data/
│   ├── business_cases.txt          (existing — curated teaching cases)
│   └── argos_reports.txt           (NEW — all 195 reports, mechanical)
├── src/
│   └── argos_extractor.py          (NEW — parses ArgosDoc/*.html → argos_reports.txt)
└── ARGOS_INTEGRATION_PILOT.md      (this file)
```

### `data/argos_reports.txt` schema

Pipe-delimited like `business_cases.txt`. One row per report.

```
REPORT_ID|TITLE|SUBREPORTS|TABLES|PARAMETERS|SQL|SOURCE_FILE
AR001|IDES Quarterly Wages|HR_S106 - IDES Quarterly Wage Report|PWVEARN,PWVEMPS|main_MC_quarter,main_EB_payroll_year|<sql one-line>|IDES Quarterly Wages.html
```

Notes on each column:
- **REPORT_ID** — `AR001`–`AR195`, assigned in alphabetical order of source filename
- **TITLE** — the `<h1>` text from the HTML
- **SUBREPORTS** — comma-separated list from the `Reports` section (often the actual report code, e.g. `HR_S106`)
- **TABLES** — comma-separated, from the `Database Tables` section
- **PARAMETERS** — comma-separated bind variable names extracted from SQL (`:main_xxx` → `main_xxx`)
- **SQL** — the full SQL query, with newlines collapsed to spaces and pipes escaped (`\|` if any) — keep it parseable
- **SOURCE_FILE** — relative filename inside `ArgosDoc/`, for round-tripping

---

## The 4 concrete tasks

### Task 1 — Write `src/argos_extractor.py`

A standalone Python script (no jinja, no other deps beyond stdlib + maybe `beautifulsoup4` for HTML parsing).

**Contract:**
```bash
python src/argos_extractor.py \
    --input  C:/Proyecto/Waubonsee/argos_tool/ArgosDoc \
    --output data/argos_reports.txt
```

**Behavior:**
1. Glob all `*.html` files in input dir (skip `index.html`).
2. For each file, parse:
   - `<h1>` → title
   - `Reports` `<ul>` → subreports
   - `Database Tables` `<table>` → tables (extract `<td>` from rows after the header)
   - `<pre class='language-sql'>` → SQL (HTML-decode `&lt;` `&gt;` `&#x27;` etc., collapse whitespace to single spaces)
   - SQL bind vars: regex `:([A-Za-z_][\w.]*)`, dedupe, strip trailing `.Quarter` style suffixes from Argos chained refs
3. Assign `AR001`–`ARNNN` in sorted-filename order.
4. Write `data/argos_reports.txt` with header.
5. Print summary: count of reports parsed, count by table reference, list of files where SQL extraction failed.

**Acceptance:** running it on the current 195 files produces a 196-line file (header + 195 rows), no parse errors logged.

### Task 2 — Wire `argos_reports.txt` into the build

**Edit `src/generator.py`:**
- Load `data/argos_reports.txt` if it exists (optional file — don't fail if missing).
- Parse into a JSON-serializable list, similar to how `business_cases_json` is currently built.
- Pass into the Jinja template as `argos_reports_json`.

**Edit `templates/index.html`:**
- Add a JS const `var ARGOS_REPORTS = {{ argos_reports_json | default('[]') }};` near where `BUSINESS_CASES` is declared.
- Add a new function `findMatchingArgosReports(tables)` — same pattern as `findMatchingCases`, returns top 5 reports by table-overlap score.
- In `buildExplanation()`, after the existing `Related Business Cases` section, add a `Production Argos Reports` section that calls the new function and renders each match: title, source file, table overlap count, and a one-line snippet of what tables match.

**Acceptance:** open `docs/index.html`, paste a query touching `PWVEARN`, see at least `IDES Quarterly Wages` in the new "Production Argos Reports" section.

### Task 3 — Curate the Tier-2 shortlist

Spend an hour reviewing the auto-generated `argos_reports.txt`. For each candidate below, decide:
- **canonical** → promote to `business_cases.txt` with a written-up BC entry
- **legacy** → leave in `argos_reports.txt`, do not promote (add a `# legacy` note in the BC if you want one for the warning)
- **export-only** → leave alone, no BC needed

**Tax/Payroll candidate shortlist (12 reports):**

| Filename | Why it's a candidate |
|---|---|
| `IDES Quarterly Wages.html` | Ground truth for SUI row-level SE9000 — already validated against this Apr 8 |
| `Monthly Wages.html` | Monthly SUI counterpart — confirms our `get_monthly_sui_wages` logic |
| `Quarterly Wages.html` | Generic quarterly wage — sanity check vs SUI variant |
| `FIM and FIO Quarterly Contributions.html` | Medicare + SS contributions, ER + EE breakdown |
| `IL 941 Schedule P.html` | Federal 941 — the truth source for Q1 reconciliation |
| `IRS Audit Data.html` | Audit reference — what IRS-relevant queries look like |
| `Electronic W-2.html` | W-2 year-end data assembly |
| `Electronic W-2 Consents.html` | Often paired with above |
| `Employee SURS Deductions.html` | SURS/SS exemption (ties to existing BC006) |
| `Employees with Active SURS and FIO Deductions.html` | Anomaly check — rare to have both |
| `Payroll Deduction Register.html` | Tax withholding detail |
| `Deduction by Deduction Code.html` | Deduction taxonomy |

For each promoted entry, the BC should:
- Cite the Argos report by ID (`AR0xx`) and filename in `LEARNED_FROM`
- Note any difference between what the report does and what we now consider best practice

### Task 4 — Document in `README.md`

Add a short section to the project README describing:
- The `argos_reports.txt` data file and what it represents
- The "Production Argos Reports" section in the SQL Explainer
- How to refresh: re-run `argos_extractor.py` after Argos exports change

---

## Quality gates before merging

1. **`argos_reports.txt` parses cleanly** — run `python -c "open('data/argos_reports.txt').read().splitlines()"` then verify column count = 7 on every row.
2. **No SQL contains literal newlines or unescaped pipes** — these would break the pipe-delimited format.
3. **Build still succeeds** — `python build.py` produces `docs/index.html` without warnings.
4. **SQL Explainer surfaces matches** — paste 3 test queries and verify the new section appears with sensible matches:
   - Query touching `PWVEARN` → should match `IDES Quarterly Wages`, `Monthly Wages`, `Quarterly Wages`
   - Query touching `PHRDEDN` + `PTRBDCA` → should match `Deduction by Deduction Code`
   - Query touching only `SPRIDEN` → should match employee-list-style reports
5. **Existing BM25 search and SQL Explainer regress nothing** — sanity check the original test queries from the README still work.

---

## What we are NOT doing in this pilot

- Not auto-importing all 195 reports into `business_cases.txt`. Only Tier 2 (curated) goes there.
- Not modifying any Argos source. Read-only consumer.
- Not touching the chatbot pieces (`enhanced_chatbot_server.py`, `OllamaClient.py`, etc.). The argos_tool project has its own AI layer; we are only consuming the static HTML output.
- Not building a UI to edit Argos reports. View only.

---

## Open questions to resolve as we go

1. **Argos parameter naming** — bind vars are like `:main_MC_quarter.Quarter`. Do we keep the `.Quarter` suffix in `PARAMETERS` or strip it? Probably strip — users will type the parameter name without the chain accessor.
2. **Subreports field** — sometimes 1, sometimes 4+ entries. Is the ID part (`HR_S106`) more useful than the description? Probably yes — keep just the IDs in `SUBREPORTS`, drop the descriptive text.
3. **SQL with comments** — some reports have `-- HR_S106` style header comments. Strip or keep? Probably keep as-is, they're semantically meaningful.
4. **Conflicting reports** — if two Argos reports answer the "same" question with different SQL (e.g., `Gross Pay Distribution by FOAP.html` vs `Gross Pay Distribution by FOAP (fixed).html`), which do we point users to? In Tier 1, both surface — let users decide. In Tier 2, only the canonical version gets a BC.

---

## Estimated effort

| Task | Time |
|---|---|
| 1. Write extractor + verify on all 195 files | 45 min |
| 2. Wire into build + template + verify in browser | 60 min |
| 3. Curate 12 candidates → ~10 BC entries | 90 min |
| 4. README update | 15 min |
| **Total** | **~3.5 hours** |

Best done in a dedicated session in this project, not mixed with ADP work.

# Banner Schema Search

A smart, self-contained search tool for Ellucian Banner database schema. Search 6,900+ tables and 133,000+ columns instantly. **No AI, no server, no internet required** -- just open one HTML file in any browser.

> "How does it work so well without AI?" -- It uses the same algorithms that powered Google Search and Elasticsearch for decades. Pure math, zero magic.

---

## Quick Start (3 steps)

```bash
# 1. Install the only dependency
pip install jinja2

# 2. Build the site (takes ~2 seconds)
python build.py

# 3. Open in your browser
# Windows:
start docs\index.html
# Mac/Linux:
open docs/index.html
```

That's it. You now have a fully searchable Banner data dictionary.

---

## What Can You Search?

Type natural English and the tool understands Banner abbreviations automatically:

| You type                    | It also searches for                        |
|-----------------------------|---------------------------------------------|
| `employee hire date`        | EMPL, EMP, PEBEMPL, HIRED, EMPLOYMENT      |
| `payroll deductions`        | PAY, PHR, PHRHIST, DEDN, DED, BDCA         |
| `person address`            | PERS, PIDM, SPRIDEN, ADDR, SPRADDR          |
| `salary compensation`       | WAGE, PAY, EARNINGS, GROSS, NET             |
| `course registration`       | CRSE, CLASS, SECTION, ENROLL                |
| `degree major`              | DGRE, MAJR, PROGRAM, CONCENTRATION          |

It also handles typos: `employy` still finds "employee", `addres` finds "address".

---

## Features

### Search
- **BM25 Ranking** -- The same algorithm Elasticsearch uses. Ranks results by true relevance, not just keyword matching.
- **Banner Synonym Expansion** -- Automatically translates between natural English and Banner's abbreviated naming conventions.
- **Fuzzy Matching** -- Handles typos using trigram similarity (character-level matching).
- **Interactive Term Builder** -- After searching, you see all active search terms as toggleable tags. Remove synonyms that add noise, add your own terms, and results update in real-time.
- **Refine Within Results** -- A secondary search bar to filter within your current results.
- **Cross-Reference** -- Search for `_PIDM` to find every table in Banner that links to a person.

### Browse
- **Module Browser** -- Tables organized by Banner functional area: Student, HR/Payroll, Finance, Financial Aid, Advancement, Accounts Receivable, Position Control, General.
- **Table Detail View** -- Click any table to see all its columns with full descriptions.
- **Column Pattern Badges** -- Automatic color-coded labels: `Person ID` for _PIDM columns, `Code` for _CODE, `Indicator` for _IND, `Date` for _DATE, `Amount` for _AMT, `Key` for _SURROGATE_ID.
- **Related Tables** -- When viewing a table, see other tables that share the same key columns (PIDM, TERM_CODE, etc.).

### SQL Explainer & Validator
Paste any Banner SQL query and the tool inspects it against the live schema and a curated knowledge base of real Banner integration cases.

- **Schema validation** -- Every table and column referenced in the query is checked against the embedded Banner schema. Unknown identifiers are flagged with "Did you mean...?" suggestions powered by Levenshtein distance.
- **Banner pitfall detection** -- Catches the gotchas that have burned real integrations:
  - `PHRHIST` used without `PHRHIST_DISP >= '60'` filter (in-progress vs posted)
  - Payroll tables without a `PICT_CODE` filter
  - `SPRIDEN` without `CHANGE_IND IS NULL` (current vs historical names)
  - `SPRADDR` with student address types (`MA`/`RE`) instead of `HR` for employees
  - `PEBEMPL_CURRENT_HIRE_DATE` vs `PEBEMPL_FIRST_HIRE_DATE` for tax reporting
  - `PHRHIST_GROSS > 0` filter that excludes negative reversal records
  - `PERETOT` for SUI/unemployment without student-employment exclusion
  - Stale `PXRW2ST` for state assignment vs the more reliable `PWVEMPL_MAIL_STATE`
- **Function-aware parser** -- Correctly handles SQL standard functions that use the `FROM` keyword internally: `EXTRACT(MONTH FROM col)`, `TRIM(LEADING ' ' FROM col)`, and `SUBSTRING(col FROM n FOR m)`. These won't be misread as table references.
- **Business case matching** -- Compares your query's tables to a knowledge base (`data/business_cases.txt`) of real-world Banner integration scenarios (Federal/Medicare/SS tax, SURS exemptions, payroll adjustments, W-2 reporting, etc.) and surfaces matching cases with their lessons learned.
- **Structural checks** -- Balanced parentheses, missing `SELECT`/`FROM`, and aggregation hints.
- **All offline** -- The validator runs entirely in the browser using the embedded schema. Your SQL never leaves your machine.

### UI
- **Help Panel** -- Click "? HELP" on the right edge (or press `?`) for a complete guide with 50+ clickable example queries, including real-world integration scenarios.
- **Dark Mode** -- Automatically matches your system theme.
- **Keyboard Shortcuts** -- `/` to focus search, `?` for help, `Escape` to close panels.
- **Filters** -- Filter by type (TABLE/VIEW) and by module.
- **Responsive** -- Works on desktop, tablet, and mobile.
- **Offline** -- Everything is in a single HTML file. No internet, no server, no dependencies at runtime.

---

## How Does It Work Without AI?

This is the question everyone asks. The answer: **the same techniques that powered search engines for 30 years before LLMs existed.**

### 1. BM25 Ranking (the core algorithm)

BM25 (Best Matching 25) was developed in the 1990s and is still the default ranking algorithm in Elasticsearch, Apache Lucene, and Apache Solr. Google used a variant of it for years.

The formula:

```
score(Document, Query) = sum for each query term of:
    IDF(term) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * docLength / avgDocLength))
```

Where:
- **IDF** (Inverse Document Frequency) = how rare a word is. "PIDM" is rare and important; "the" is common and worthless.
- **tf** = how many times the word appears in this specific document.
- **k1** and **b** are tuning parameters (we use standard values: k1=1.5, b=0.75).
- **docLength / avgDocLength** = normalizes for document length so short, focused descriptions aren't penalized.

**In plain English:** A document scores high when it contains rare, important words from your query, especially if those words appear frequently relative to the document's length.

### 2. Banner Synonym Expansion (the secret sauce)

Banner uses abbreviated names like `PEBEMPL_ECLS_CODE`. Humans search for "employee class code". The tool bridges this gap with a hand-curated synonym map:

```python
'employee': ['empl', 'emp', 'pebempl']
'address':  ['addr', 'spraddr', 'street', 'city', 'state', 'zip']
'salary':   ['wage', 'pay', 'compensation', 'earnings']
```

When you search "employee hire date", the engine:
1. Tokenizes your query: `['employee', 'hire', 'date']`
2. Expands with synonyms: adds `empl`, `emp`, `pebempl`, `hired`, `employment`, `dt`
3. Searches for ALL of these terms (synonyms at 40% weight so originals rank higher)
4. Returns results ranked by BM25

This is what makes it feel "intelligent" -- it's not AI, it's **domain knowledge encoded as data**.

### 3. Fuzzy Matching (typo tolerance)

Uses trigram similarity -- the same technique used by PostgreSQL's `pg_trgm` extension:

1. Break words into 3-character chunks: `employee` -> `$$e`, `$em`, `emp`, `mpl`, `plo`, `loy`, `oye`, `yee`, `ee$`, `e$$`
2. Compare trigram overlap between your misspelled word and all index terms
3. Calculate Jaccard similarity: `intersection / union`
4. If similarity > 25%, include those results at reduced weight

### 4. Build-Time Indexing (why it's fast)

All the heavy computation happens once, at build time (the `python build.py` step):

```
table_info.txt + field_info.txt
    |
    v
[Python: Parse -> Tokenize -> Stem -> Calculate BM25 -> Build Inverted Index]
    |
    v
index.html (with all data + index embedded as JSON)
    |
    v
[Browser: Tokenize query -> Lookup index -> Rank -> Display]
```

The browser only does hash-map lookups and simple math. That's why search is instant even with 133,000+ columns.

---

## Project Structure

```
BannerSemanticSearch/
├── build.py              # Main build script - run this to generate the site
├── requirements.txt      # Python dependency: jinja2
├── src/
│   ├── parser.py         # Reads table_info.txt and field_info.txt
│   │                     #   Handles multi-line descriptions and edge cases
│   ├── categorizer.py    # Maps table prefixes to Banner modules
│   │                     #   (SP->Student, PE->HR, FB->Finance, etc.)
│   ├── indexer.py        # Builds the BM25 inverted index
│   │                     #   Also: synonym map, trigram index, column patterns,
│   │                     #   related tables index
│   └── generator.py      # Renders the Jinja2 template with embedded data
├── templates/
│   └── index.html        # The Single Page Application template
│                         #   Contains: HTML structure, CSS styles, JavaScript
│                         #   search engine, router, and all UI components
├── data/                 # Input data files (pipe-delimited)
│   ├── table_info.txt        #   TABLE_NAME|TYPE|DESCRIPTION
│   ├── field_info.txt        #   TABLE_NAME|COLUMN_NAME|DESCRIPTION
│   ├── relationships.txt     #   Foreign key constraints (optional)
│   └── business_cases.txt    #   Curated Banner integration knowledge
│                             #   (used by the SQL Explainer for case matching)
└── docs/                 # Generated output
    └── index.html        # THE OUTPUT - open this in your browser
                          #   Self-contained: ~17 MB, works offline
```

### How each Python module works

**`src/parser.py`** -- Reads the pipe-delimited data files. Handles an edge case where some table descriptions in `table_info.txt` span multiple lines (detected by checking if a line starts with a valid `TABLE_NAME|TYPE|` pattern). Creates `TableInfo` objects with attached `ColumnInfo` lists.

**`src/categorizer.py`** -- Maps each table to a Banner module using its name prefix. Banner naming convention: first 2 characters indicate the functional area (SP = Student/Person, PE = Payroll/Employee, FB = Finance/Budget, etc.). Contains a comprehensive prefix-to-module mapping with ~80 prefixes across 13 modules.

**`src/indexer.py`** -- The algorithmic heart. Does these steps:
1. Tokenize all text (split on spaces/underscores, lowercase, remove stop words, simple stem)
2. Calculate document frequency for each token
3. Calculate BM25 IDF: `log((N - df + 0.5) / (df + 0.5) + 1)`
4. For each document, calculate BM25 score per token with length normalization
5. Build inverted index: `{token -> [(table_id, column_index, score), ...]}`
6. Build trigram index for fuzzy matching
7. Build related tables index (tables sharing key columns like _PIDM, _TERM_CODE)
8. Export synonym map and column pattern definitions

**`src/generator.py`** -- Takes all the data and renders it into the Jinja2 template. The schema data (all tables + columns) and search index are serialized as compact JSON and embedded directly in the HTML as `<script>` variables. This ensures the file works offline via `file://` protocol (no CORS issues with external JSON files).

**`templates/index.html`** -- A complete Single Page Application in one file. Contains:
- CSS with light/dark theme support via `prefers-color-scheme`
- Hash-based router (`#/table/SPRIDEN`, `#/module/Student`, `#/search/query`)
- JavaScript search engine that mirrors the Python tokenizer/stemmer exactly
- Synonym expansion, fuzzy matching, and BM25 scoring at runtime
- Interactive term builder with add/remove/toggle
- Grouped search results with expand/collapse
- Column pattern badge detection
- Help panel with 50+ example queries
- SQL Explainer/Validator: parses SQL queries (EXTRACT/TRIM/SUBSTRING aware), validates tables and columns against the embedded schema, runs Banner pitfall checks, and matches against the business-case knowledge base

---

## Data Extraction Guide

The search tool needs 3 data files extracted from your Banner Oracle database. Below are the exact steps to generate each one.

### Prerequisites

- Access to Banner's Oracle database (SQL Developer, TOAD, SQL*Plus, or any Oracle client)
- SELECT privileges on the schemas: `SATURN`, `PAYROLL`, `POSNCTL`, `BANINST1`, `GENERAL`, `FIMSMGR`
- Adjust the schema list in the `WHERE` clause if your institution uses different schema names

### File 1: `table_info.txt` -- Table/View definitions

This file lists every table and view with its description.

**Format:** `TABLE_NAME|TYPE|DESCRIPTION` (pipe-delimited, one per line)

**SQL Query:**
```sql
SELECT trim(dtc.TABLE_NAME) || '|' ||
       CASE WHEN atc.TABLE_TYPE = 'TABLE' THEN 'TABLE' ELSE 'VIEW' END || '|' ||
       trim(NVL(atc.COMMENTS, '(no comments)'))
FROM   dba_tab_columns dtc
INNER JOIN all_tab_comments atc
       ON atc.TABLE_NAME = dtc.TABLE_NAME
       AND atc.OWNER = dtc.OWNER
WHERE  dtc.OWNER IN ('SATURN', 'PAYROLL', 'POSNCTL', 'BANINST1', 'GENERAL', 'FIMSMGR')
ORDER BY dtc.TABLE_NAME;
```

**Alternative (if you don't have DBA access):**
```sql
SELECT trim(TABLE_NAME) || '|' || TABLE_TYPE || '|' ||
       trim(NVL(COMMENTS, '(no comments)'))
FROM   all_tab_comments
WHERE  OWNER IN ('SATURN', 'PAYROLL', 'POSNCTL', 'BANINST1', 'GENERAL', 'FIMSMGR')
ORDER BY TABLE_NAME;
```

**SQL*Plus example:**
```sql
SET LINESIZE 2000
SET PAGESIZE 0
SET FEEDBACK OFF
SET HEADING OFF
SET TRIMSPOOL ON
SET LONG 4000
SPOOL table_info.txt

-- paste the query here

SPOOL OFF
```

**SQL Developer:** Run the query > right-click results > Export > Format: Text, Delimiter: `|` > Save as `table_info.txt`

---

### File 2: `field_info.txt` -- Column definitions

This file lists every column in every table with its description.

**Format:** `TABLE_NAME|COLUMN_NAME|DESCRIPTION` (pipe-delimited, one per line)

**SQL Query:**
```sql
SELECT trim(c.TABLE_NAME) || '|' ||
       c.COLUMN_NAME || '|' ||
       trim(NVL(c.COMMENTS, '(no comments)'))
FROM   ALL_COL_COMMENTS c
WHERE  c.OWNER IN ('SATURN', 'PAYROLL', 'POSNCTL', 'BANINST1', 'GENERAL', 'FIMSMGR')
ORDER BY c.TABLE_NAME, c.COLUMN_NAME;
```

**SQL*Plus example:**
```sql
SET LINESIZE 2000
SET PAGESIZE 0
SET FEEDBACK OFF
SET HEADING OFF
SET TRIMSPOOL ON
SET LONG 4000
SPOOL field_info.txt

SELECT trim(c.TABLE_NAME) || '|' ||
       c.COLUMN_NAME || '|' ||
       trim(NVL(c.COMMENTS, '(no comments)'))
FROM   ALL_COL_COMMENTS c
WHERE  c.OWNER IN ('SATURN', 'PAYROLL', 'POSNCTL', 'BANINST1', 'GENERAL', 'FIMSMGR')
ORDER BY c.TABLE_NAME, c.COLUMN_NAME;

SPOOL OFF
```

> **Note:** This is the largest file (~11 MB, 130K+ rows). It may take 10-30 seconds to run depending on your database.

---

### File 3: `relationships.txt` -- Foreign key constraints (optional but recommended)

This file lists every formal foreign key relationship between tables. Without this file, the tool still infers ~10,000 relationships from Banner naming conventions. With this file, you get the full picture (~15,000 relationships).

**Format:** `CHILD_TABLE|CHILD_COLUMN|PARENT_TABLE|PARENT_COLUMN|CONSTRAINT_NAME` (pipe-delimited)

**SQL Query:**
```sql
SELECT cc.TABLE_NAME || '|' ||
       cc.COLUMN_NAME || '|' ||
       rc.TABLE_NAME || '|' ||
       rc.COLUMN_NAME || '|' ||
       c.CONSTRAINT_NAME
FROM   all_constraints c
JOIN   all_cons_columns cc
       ON cc.CONSTRAINT_NAME = c.CONSTRAINT_NAME
       AND cc.OWNER = c.OWNER
JOIN   all_cons_columns rc
       ON rc.CONSTRAINT_NAME = c.R_CONSTRAINT_NAME
       AND rc.OWNER = c.R_OWNER
       AND rc.POSITION = cc.POSITION
WHERE  c.CONSTRAINT_TYPE = 'R'
       AND c.OWNER IN ('SATURN', 'PAYROLL', 'POSNCTL', 'BANINST1', 'GENERAL', 'FIMSMGR')
ORDER BY cc.TABLE_NAME, cc.COLUMN_NAME;
```

**SQL*Plus example:**
```sql
SET LINESIZE 500
SET PAGESIZE 0
SET FEEDBACK OFF
SET HEADING OFF
SET TRIMSPOOL ON
SPOOL relationships.txt

SELECT cc.TABLE_NAME || '|' ||
       cc.COLUMN_NAME || '|' ||
       rc.TABLE_NAME || '|' ||
       rc.COLUMN_NAME || '|' ||
       c.CONSTRAINT_NAME
FROM   all_constraints c
JOIN   all_cons_columns cc
       ON cc.CONSTRAINT_NAME = c.CONSTRAINT_NAME
       AND cc.OWNER = c.OWNER
JOIN   all_cons_columns rc
       ON rc.CONSTRAINT_NAME = c.R_CONSTRAINT_NAME
       AND rc.OWNER = c.R_OWNER
       AND rc.POSITION = cc.POSITION
WHERE  c.CONSTRAINT_TYPE = 'R'
       AND c.OWNER IN ('SATURN', 'PAYROLL', 'POSNCTL', 'BANINST1', 'GENERAL', 'FIMSMGR')
ORDER BY cc.TABLE_NAME, cc.COLUMN_NAME;

SPOOL OFF
```

> **Note:** This file is optional. If it doesn't exist in the `data/` directory, the tool still works -- it infers relationships from Banner column naming conventions (e.g., any column ending in `_PIDM` links to SPRIDEN).

---

### Summary: Place the files

After extraction, place all files in the `data/` directory:

```
BannerSemanticSearch/
└── data/
    ├── table_info.txt          # ~6,600 lines (~450 KB)
    ├── field_info.txt          # ~130,000 lines (~11 MB)
    └── relationships.txt       # ~6,500 lines (~500 KB) [optional]
```

Then build:
```bash
python build.py
```

Output:
```
Found 6,668 tables/views with 133,946 columns
Building BM25 search index: 18,013 tokens
Building table relationships: 15,104 relationships across 4,233 tables
Build complete in 2.5s
```

---

### Updating the Data

When Banner is upgraded or schema changes (new tables, renamed columns, etc.):

1. Re-run the 3 SQL queries above
2. Replace the files in the `data/` directory
3. Run `python build.py`
4. New `docs/index.html` is generated in ~2.5 seconds
5. Share the updated file with your team

---

### Troubleshooting

**"Permission denied" on DBA views:**
Use the `all_tab_comments` alternative query for `table_info.txt`. Your DBA can also grant SELECT on `dba_tab_columns` if needed.

**Output has double quotes or header lines:**
The parser automatically strips leading/trailing double quotes and skips header lines. No manual cleanup needed.

**Missing schemas:**
Check which schemas your institution uses. Some Banner installations use different schema names. Run this query to see available schemas:
```sql
SELECT DISTINCT OWNER FROM all_tab_comments WHERE OWNER LIKE '%BAN%' OR OWNER IN ('SATURN','PAYROLL','POSNCTL','BANINST1','GENERAL','FIMSMGR');
```

**Large output files:**
The `field_info.txt` file is typically 10-12 MB. This is normal -- Banner has 130,000+ columns. The build script handles this in ~2 seconds.

---

## Sharing with Your Team

### Option 1: Just send the file
Send `docs/index.html` to anyone. They open it in Chrome/Firefox/Edge. Done.

### Option 2: GitHub Pages
1. Push the repo to GitHub
2. Go to Settings > Pages > Source: Deploy from `docs/` folder
3. Share the URL

### Option 3: Shared network drive
Copy `docs/index.html` to a shared drive. Anyone can open it from there.

### Option 4: Run locally from source
```bash
git clone <repo-url>
cd BannerSemanticSearch
pip install jinja2
python build.py
start docs\index.html
```

---

## FAQ

**Q: How big is the output file?**
A: ~17 MB (10 MB schema data, 6 MB search index, 44 KB application code). Opens instantly in any modern browser. On GitHub Pages with gzip compression, it downloads as ~3-4 MB.

**Q: Does it need internet?**
A: No. Everything is in one HTML file. Open it from your desktop, a USB drive, anywhere.

**Q: Does it use AI or machine learning?**
A: No. Zero AI. The search uses BM25 (a mathematical formula from the 1990s), synonym expansion (a hand-written dictionary), and trigram matching (character-level comparison). These are the same algorithms that power Elasticsearch.

**Q: What Python version do I need?**
A: Python 3.8 or newer. The only dependency is `jinja2` (a template engine).

**Q: Can I add my own synonyms?**
A: Yes. Edit `src/indexer.py` and add entries to the `BANNER_SYNONYMS` dictionary. Then rebuild.

**Q: Can I add synonyms at search time?**
A: Yes! After searching, use the interactive term builder to add custom terms. These are session-only (reset on new search). For permanent additions, edit `src/indexer.py`.

**Q: What Banner versions does this support?**
A: Any version. The tool reads generic Oracle metadata (table/column names and comments). It works with Banner 8, Banner 9, or any version that has `ALL_TAB_COMMENTS` and `ALL_COL_COMMENTS`.

"""
Smoke test for the Oracle → PostgreSQL dialect detector.

Tests the detector function directly via window.detectOracleToPostgresDialect.
The UI integration (target-dialect dropdown) ships in the next commit; this
commit just validates the engine.
"""
from __future__ import annotations
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not installed.")
    sys.exit(1)

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / 'docs' / 'index.html'
URL = 'file:///' + str(HTML).replace('\\', '/')

#  Oracle-heavy query that should trigger most of the patterns.
ORACLE_SQL = """
-- Banner Oracle SQL that won't run on Banner SaaS PostgreSQL
SELECT /*+ INDEX(p phrhist_pidm_idx) */
       NVL(s.spriden_first_name, 'Unknown')     AS first_name,
       NVL2(s.spriden_mi, s.spriden_mi, '-')     AS middle_init,
       DECODE(p.phrhist_disp, '60', 'Posted', 'Pending') AS status,
       LISTAGG(p.phrhist_bdca_code, ',')
           WITHIN GROUP (ORDER BY p.phrhist_bdca_code) AS deductions,
       MONTHS_BETWEEN(SYSDATE, e.pebempl_first_hire_date) AS months_employed,
       ADD_MONTHS(e.pebempl_first_hire_date, 12)         AS one_year_later,
       INSTR(s.spriden_last_name, '-')           AS dash_pos,
       my_audit_seq.NEXTVAL                       AS audit_id
FROM   spriden s, phrhist p, pebempl e,
       (SELECT LEVEL AS lvl FROM dual CONNECT BY LEVEL <= 12) months
WHERE  p.phrhist_pidm = s.spriden_pidm
   AND e.pebempl_pidm(+) = s.spriden_pidm
   AND ROWNUM <= 100
MINUS
SELECT NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL FROM dual
"""

#  Each entry: (keyword that MUST appear in at least one msg)
EXPECTED_KEYWORDS = [
    'SYSDATE', 'NVL', 'NVL2', 'DECODE', 'LISTAGG',
    'CONNECT BY LEVEL', 'FROM dual', 'ROWNUM', '(+)',
    'MONTHS_BETWEEN', 'ADD_MONTHS', 'NEXTVAL',
    'MINUS', 'INSTR', 'optimizer hints',
]


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.goto(URL, wait_until='domcontentloaded')
        page.wait_for_function("typeof window.detectOracleToPostgresDialect === 'function'", timeout=8000)

        hints = page.evaluate(f"window.detectOracleToPostgresDialect({ORACLE_SQL!r})")
        print(f"Detected {len(hints)} Oracle-only construct(s):")
        for h in hints:
            print(f"  - {h['msg']}")
        print()

        joined = '\n'.join(h['msg'] + ' ' + (h.get('suggestion') or '') for h in hints)
        missing = [kw for kw in EXPECTED_KEYWORDS if kw not in joined]
        if missing:
            print(f"!! Missing detection for: {missing}")
            return 1

        #  Spot-check that Copy-fix snippets exist for the mechanical translations
        fix_count = sum(1 for h in hints if h.get('fixSnippet'))
        print(f"{fix_count} hint(s) carry a mechanical Copy-fix snippet")
        assert fix_count >= 10, f"Expected ≥10 fixable hints, got {fix_count}"

        #  Verify clean SQL produces zero hints (no false positives on plain Oracle-portable SQL)
        clean_sql = "SELECT s.spriden_id, s.spriden_first_name FROM spriden s WHERE s.spriden_change_ind IS NULL"
        clean_hints = page.evaluate(f"window.detectOracleToPostgresDialect({clean_sql!r})")
        print(f"Clean SQL produced {len(clean_hints)} hint(s) (expected 0)")
        assert len(clean_hints) == 0, f"Clean Oracle-portable SQL should produce no hints, got {len(clean_hints)}: {[h['msg'] for h in clean_hints]}"

        print()
        print(f"OK — {len(hints)} Oracle-only constructs detected (≥{len(EXPECTED_KEYWORDS)} expected patterns covered).")
        return 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except AssertionError as exc:
        print(f"!! ASSERTION FAILED: {exc}")
        sys.exit(1)

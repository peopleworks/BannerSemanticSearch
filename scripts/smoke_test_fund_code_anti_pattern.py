"""
Headless smoke test for the hardcoded *_fund_code IN-list anti-pattern hint.

Confirms:
  1. FIRES on a 5+ literal IN-list against *_fund_code (the real FAID1026
     OTHER subquery shape) and surfaces the EXCLUDE-pattern suggestion.
  2. DOES NOT fire on a 4-literal IN-list (below threshold — likely a
     legitimate small enum).
  3. DOES NOT fire on a 5+ literal IN-list against a non-fund column
     (e.g. ptrm_code, term_code, day-of-week) — narrowness guarantees
     low false-positive rate.
  4. The warning's fixSnippet shows a NOT IN replacement so the user
     can click the Copy-fix button next to it.
"""
from __future__ import annotations
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not installed. pip install playwright && playwright install chromium")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / 'docs' / 'index.html'
URL = 'file:///' + str(HTML).replace('\\', '/')


#  Case 1 — should FIRE. This is the actual FAID1026 OTHER subquery shape
#  (10 literals on *_fund_code).
SHOULD_FIRE_SQL = """
SELECT SUM(ofx.rprawrd_offer_amt)
  FROM rprawrd ofx
 WHERE ofx.rprawrd_pidm = 12345
   AND ofx.rprawrd_aidy_code = '2526'
   AND ofx.rprawrd_fund_code IN ('ADMITS','ATHL','EMERG','EMPWAV','FDN','GUST','ING','IVG','PSCH','MIAPOW')
"""

#  Case 2 — should NOT fire. 4 literals on *_fund_code is below threshold.
BELOW_THRESHOLD_SQL = """
SELECT SUM(rprawrd_offer_amt)
  FROM rprawrd
 WHERE rprawrd_aidy_code = '2526'
   AND rprawrd_fund_code IN ('PELL','MAP','SEOG','FWS')
"""

#  Case 3 — should NOT fire. 7 literals but on a non-fund column. The
#  validator must be narrow enough to leave legitimate enums alone.
NON_FUND_COL_SQL = """
SELECT *
  FROM sobptrm
 WHERE sobptrm_term_code = '2526'
   AND sobptrm_ptrm_code IN ('F','F1M','F2T','F3W','F4R','F5F','S8')
"""


def _validate(page, sql, label):
    page.evaluate("location.hash = '#/sql'")
    page.wait_for_selector('#sqlInput', timeout=5000)
    page.fill('#sqlInput', sql)
    page.click('#sqlExplainBtn')
    page.wait_for_selector('#sqlResults', timeout=5000)
    page.wait_for_timeout(300)
    text = page.inner_text('#sqlResults')
    print(f"  [{label}] results length: {len(text)} chars")
    return text


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)
        page.wait_for_load_state('networkidle')

        #  --- Case 1: should FIRE ---
        results1 = _validate(page, SHOULD_FIRE_SQL, 'should_fire')
        lower1 = results1.lower()
        assert 'include-list anti-pattern' in lower1, \
            "Anti-pattern hint did not fire on a 10-literal _fund_code IN-list"
        assert 'rprawrd_fund_code' in lower1, \
            "Warning should name the offending column (rprawrd_fund_code)"
        assert '1,361,345' in results1 or '$1,361,345' in results1, \
            "Suggestion should cite the real Waubonsee audit number ($1,361,345)"
        assert 'not in' in lower1, "fixSnippet should suggest NOT IN replacement"
        print("[OK] Anti-pattern warning fires on 10-literal _fund_code IN-list")
        print("     and surfaces $1,361,345 + NOT IN suggestion")

        #  --- Case 2: should NOT fire (below threshold) ---
        results2 = _validate(page, BELOW_THRESHOLD_SQL, 'below_threshold')
        lower2 = results2.lower()
        assert 'include-list anti-pattern' not in lower2, \
            "False positive: hint fired on 4-literal IN-list (should be >= 5)"
        print("[OK] Hint does NOT fire on 4-literal IN-list (threshold respected)")

        #  --- Case 3: should NOT fire (non-fund column) ---
        results3 = _validate(page, NON_FUND_COL_SQL, 'non_fund_col')
        lower3 = results3.lower()
        assert 'include-list anti-pattern' not in lower3, \
            "False positive: hint fired on 7-literal IN-list on ptrm_code (not _fund_code)"
        print("[OK] Hint does NOT fire on 7-literal ptrm_code IN-list (column scope respected)")

        browser.close()
    print("\n[PASS] smoke_test_fund_code_anti_pattern.py")


if __name__ == '__main__':
    main()

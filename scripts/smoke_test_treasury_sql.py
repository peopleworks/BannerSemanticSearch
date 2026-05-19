"""
Headless smoke test for the Treasury / Accounts-Receivable collections SQL
(uses TBRACCD, TBBDETC, SOBPTRM, SPRIDEN, SPBPERS). Confirms:

  1. TBRACCD and TBBDETC — which are NOT in our schema bundle because the
     BANSECR account doesn't see TAISMGR base tables — are downgraded from
     ERROR ("Table not found") to WARNING ("matches Banner's 7-character
     naming convention but isn't in this schema bundle").
  2. The Expand button is present on the editor and toggling it adds the
     .expanded class to .sql-editor.
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

TREASURY_SQL = """-- 5/15/26 Testing and determined that this report will work.
select 'INDIVIDUAL' as Individual_Business,
        spbpers_ssn,
        spriden_first_name,
        spriden_last_name,
        '' as Business_Name,
        twvaccs_acct_bal_numeric,
        spriden_id,
        'AT' as Reason_For_Debt,
        '01' as Notification_Type,
        '01' as Hearing_Type,
        '01' as Outcome_Type,
        to_char(sobptrm_start_date,'MM/DD/YYYY') as sobptrm_start_date,
        to_char(sobptrm_end_date,'MM/DD/YYYY') as sobptrm_end_date1,
        to_char(sobptrm_end_date,'MM/DD/YYYY') as sobptrm_end_date2
from
(
select distinct
  spbpers_ssn,
  spriden_last_name,
  spriden_first_name,
  nvl(spriden_mi,' ') as spriden_mi,
  spriden_id,
  NVL ( (SELECT sum(tc.tbraccd_amount*decode(td.tbbdetc_type_ind,'P',-1,1))
                FROM tbraccd  tc, tbbdetc  td
               WHERE tc.tbraccd_pidm = spriden_pidm
                    AND tc.tbraccd_detail_code = td.tbbdetc_detail_code
                    AND tc.tbraccd_term_code between :main_EB_start_term and :main_EB_end_term), 0)
               AS twvaccs_acct_bal_numeric,
   (SELECT max(soba.sobptrm_start_date) FROM sobptrm  soba
    WHERE soba.sobptrm_term_code = :main_EB_start_term
         AND soba.sobptrm_ptrm_code in ('F','F1M','F2T','F3W','F4R','F5F','S8') )
            AS sobptrm_start_date,
   (SELECT max(sobb.sobptrm_end_date) FROM sobptrm  sobb
    WHERE sobb.sobptrm_term_code = :main_EB_end_term
         AND sobb.sobptrm_ptrm_code in ('F','F1M','F2T','F3W','F4R','F5F','S8') )
            AS sobptrm_end_date
 from spriden , spbpers
 where spbpers_pidm = spriden_pidm
     and spriden_change_ind is null
     and spriden_entity_ind = 'P'
)
order by spriden_last_name, spriden_first_name, spriden_mi
"""


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)
        page.wait_for_load_state('networkidle')

        # Navigate to SQL Explainer
        page.evaluate("location.hash = '#/sql'")
        page.wait_for_selector('#sqlInput', timeout=5000)

        #  --- Test 1: Expand button exists and toggles .expanded class ---
        expand_btn = page.query_selector('#sqlEditorExpand')
        assert expand_btn is not None, "Expand button #sqlEditorExpand missing"
        editor = page.query_selector('#sqlEditor')
        cls_before = editor.get_attribute('class') or ''
        assert 'expanded' not in cls_before, "Editor starts expanded — should not"
        expand_btn.click()
        page.wait_for_timeout(150)
        cls_after = editor.get_attribute('class') or ''
        assert 'expanded' in cls_after, f"After click, class should include 'expanded': got {cls_after!r}"
        # Toggle back to keep state clean for subsequent runs
        expand_btn.click()
        page.wait_for_timeout(50)
        print("[OK] Expand button toggles .expanded class")

        #  --- Test 2: Paste SQL and validate ---
        page.fill('#sqlInput', TREASURY_SQL)
        page.click('#sqlExplainBtn')
        page.wait_for_selector('#sqlResults', timeout=5000)
        page.wait_for_timeout(400)

        results_text = page.inner_text('#sqlResults')

        # TBRACCD / TBBDETC should appear as warnings, NOT errors
        # Look for the new warning copy
        assert "TBRACCD" in results_text.upper() or "tbraccd" in results_text, \
            "TBRACCD not surfaced in results at all"
        assert "TBBDETC" in results_text.upper() or "tbbdetc" in results_text, \
            "TBBDETC not surfaced in results at all"

        # The phrase "not found in Banner schema" should NOT appear for TBRACCD/TBBDETC
        # (those are the hard-error words from the unknown-table branch)
        lower = results_text.lower()
        bad_phrases = [
            "table 'tbraccd' not found",
            "table 'tbbdetc' not found",
        ]
        for phrase in bad_phrases:
            assert phrase not in lower, f"Hard error still fires: {phrase!r} found in results"

        # The new warning copy should be present
        assert "7-character naming convention" in results_text, \
            "Expected 7-character naming convention warning copy not found"

        # SPRIDEN, SPBPERS, SOBPTRM should pass — they ARE in the bundle
        # (we just check no hard "not found" error fires for them)
        for known in ['SPRIDEN', 'SPBPERS', 'SOBPTRM']:
            phrase = f"table '{known.lower()}' not found"
            assert phrase not in lower, f"{known} should be recognized as a known table"

        print("[OK] TBRACCD / TBBDETC downgraded to warning (Banner-naming heuristic)")
        print("[OK] Known tables (SPRIDEN, SPBPERS, SOBPTRM) still recognized")

        # Count buckets for visibility
        error_count = lower.count('error') - lower.count('errors)') - lower.count('errors found')
        warn_count = results_text.count("'") if "warning" in lower else 0
        print(f"     Results length: {len(results_text)} chars")

        browser.close()
    print("\n[PASS] smoke_test_treasury_sql.py")


if __name__ == '__main__':
    main()

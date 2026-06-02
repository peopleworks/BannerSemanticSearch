"""
Headless smoke test for FA001 Orphan Fund Codes report.

Confirms:
  1. The Reports page (#/reports) renders the new "Financial Aid Audit"
     category alongside the existing Security categories.
  2. The FA001 report is listed by title.
  3. Clicking the report navigates to the SQL Explainer with the report
     SQL pre-loaded into the editor (same UX as the SR0XX reports).
  4. The pre-loaded SQL contains the customization markers and the
     RPRAWRD/RNVAND0 table references that drive the audit.
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


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)
        page.wait_for_load_state('networkidle')

        page.evaluate("location.hash = '#/reports'")
        page.wait_for_timeout(400)

        body_text = page.inner_text('body')
        lower = body_text.lower()

        #  Category headings are rendered uppercase via CSS text-transform,
        #  so compare case-insensitively.
        assert 'financial aid audit' in lower, \
            "New 'Financial Aid Audit' category not rendered on #/reports"
        assert 'orphan fund codes' in lower, \
            "FA001 report title 'Orphan Fund Codes' not on the page"
        assert 'access review' in lower, \
            "Existing 'Access Review' category should still be present"
        print("[OK] Reports page shows new FA category alongside existing ones")

        #  Navigate directly to the report detail page — this exercises the
        #  same code path the card's onclick uses (navigate('report/<id>'))
        #  and is more robust to UI changes than DOM-querying for the card.
        page.evaluate("location.hash = '#/report/FA001'")
        page.wait_for_timeout(400)
        detail_text = page.inner_text('body').lower()
        assert 'orphan fund codes' in detail_text, "Report detail page didn't load FA001"
        assert 'when to use' in detail_text, "Detail page missing 'When to use' section"
        assert 'caveats' in detail_text, "Detail page missing 'Caveats' section"
        print("[OK] Report detail page renders title, when-to-use, caveats")

        #  Click "Validate in SQL Explainer →" — this is the standard flow
        validate_btn = page.query_selector('.report-validate-btn')
        assert validate_btn is not None, "Validate button missing on report detail"
        validate_btn.click()
        page.wait_for_selector('#sqlInput', timeout=4000)
        page.wait_for_timeout(200)
        sql_now = page.eval_on_selector('#sqlInput', 'el => el.value')

        markers = [
            'CUSTOMIZE #1 — POPULATION',
            'CUSTOMIZE #2 — OWN_COLUMN_CODES',
            'CUSTOMIZE #3 — OTHER_INCLUDE_LIST',
            'rprawrd',
            'rnvand0',
            ':aid_year',
            'MISSING FROM REPORT',
        ]
        for needle in markers:
            assert needle.lower() in sql_now.lower(), \
                f"Pre-loaded SQL missing marker: {needle!r}"
        print("[OK] Clicking FA001 loads its SQL into the explainer editor")
        print(f"     SQL length: {len(sql_now)} chars, contains all 3 customization markers")

        browser.close()
    print("\n[PASS] smoke_test_fa001_orphan_report.py")


if __name__ == '__main__':
    main()

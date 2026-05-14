"""
Regression smoke test: make sure the relaxed parser still catches real phantom
columns. Uses a deliberately bad query — column 'PHRDEDN_FANTASM' doesn't
exist on PHRDEDN.
"""
from __future__ import annotations
import sys
from pathlib import Path

#  Force UTF-8 stdout — Windows defaults to cp1252 which can't print emojis
#  from the new "Copy fix" buttons that now appear inside warning messages.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not installed.")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / 'docs' / 'index.html'
URL = 'file:///' + str(HTML).replace('\\', '/')

BAD_SQL = """-- Should produce: 2 errors (one alias-qualified, one bare)
SELECT d.PHRDEDN_FANTASM,
       PHRDEDN_NOT_REAL,
       d.PHRDEDN_BDCA_CODE
FROM   PHRDEDN d
WHERE  d.PHRDEDN_YEAR = 2025
"""


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={'width': 1600, 'height': 900})
        page = ctx.new_page()
        page.goto(URL + '#/sql', wait_until='domcontentloaded')
        page.wait_for_selector('#sqlInput', timeout=8000)
        page.locator('#sqlInput').fill(BAD_SQL)
        page.locator('#sqlExplainBtn').click()
        page.wait_for_selector('.sql-val-section', timeout=8000)

        errors = page.locator('.sql-val-item.error .sql-val-msg').all_inner_texts()
        warnings = page.locator('.sql-val-item.warning .sql-val-msg').all_inner_texts()
        passes = page.locator('.sql-val-item.pass .sql-val-msg').all_inner_texts()

        print('=== ERRORS (%d) ===' % len(errors))
        for e in errors:
            print('  -', e.replace('\n', ' | '))
        print()
        print('=== WARNINGS (%d) ===' % len(warnings))
        for w in warnings:
            print('  -', w.replace('\n', ' | '))
        print()
        print('=== PASSES (%d) ===' % len(passes))
        for p in passes:
            print('  -', p.replace('\n', ' | '))

        # Must catch both fantasm columns
        caught_alias_ref = any('PHRDEDN_FANTASM' in e for e in errors)
        caught_bare_ref  = any('PHRDEDN_NOT_REAL' in e for e in errors)
        if not caught_alias_ref:
            print('!! REGRESSION: alias-qualified phantom PHRDEDN_FANTASM not caught.')
            return 1
        if not caught_bare_ref:
            print('!! REGRESSION: bare phantom PHRDEDN_NOT_REAL not caught.')
            return 1
        print()
        print('OK -- both real phantom columns detected, validator still works.')
        return 0


if __name__ == '__main__':
    sys.exit(run())

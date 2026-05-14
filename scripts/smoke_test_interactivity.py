"""
Smoke test for the new SQL Explainer interactivity:
  1. History panel appears after first validation and persists across reload.
  2. Errors with a target column are .clickable and selecting them scrolls
     the editor textarea to the matching text.
  3. Warnings with mechanical fixes expose a "Copy fix" button.
  4. Clicking a history entry restores the SQL in the editor.
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

#  Hits PHRHIST-without-DISP warning (mechanical fix) + SPRIDEN-without-CHANGE_IND
#  + a fantasm column to test click-to-jump.
TEST_SQL = """SELECT h.PHRHIST_PIDM, h.PHRHIST_GROSS, s.SPRIDEN_LAST_NAME, h.PHRHIST_FANTASM
FROM   PHRHIST h
JOIN   SPRIDEN s ON s.SPRIDEN_PIDM = h.PHRHIST_PIDM
WHERE  h.PHRHIST_YEAR = 2025
"""


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={'width': 1600, 'height': 900})
        page = ctx.new_page()

        page.goto(URL + '#/sql', wait_until='domcontentloaded')
        page.wait_for_selector('#sqlInput', timeout=8000)
        #  Wipe history once, BEFORE the first validation, so reload(...) below
        #  doesn't also wipe (an init_script would re-fire on every load).
        page.evaluate("try { localStorage.removeItem('sql_explainer_history'); } catch(e){}")
        #  Force the history panel to refresh from the now-empty storage.
        page.evaluate("var p=document.getElementById('sqlHistoryPanel'); if(p) p.style.display='none';")

        #  Initially: no history panel visible (display:none when empty)
        before_panel_visible = page.locator('#sqlHistoryPanel').is_visible()
        print(f"Before validation, history panel visible: {before_panel_visible} (expect False)")

        #  Paste + validate
        page.locator('#sqlInput').fill(TEST_SQL)
        page.locator('#sqlExplainBtn').click()
        page.wait_for_selector('.sql-val-section', timeout=8000)

        errors = page.locator('.sql-val-item.error').count()
        warnings = page.locator('.sql-val-item.warning').count()
        clickable = page.locator('.sql-val-item.clickable').count()
        fix_buttons = page.locator('.sql-fix-btn').count()
        print(f"Errors: {errors}, Warnings: {warnings}, Clickable items: {clickable}, Fix buttons: {fix_buttons}")

        #  Should have at least 1 error (PHRHIST_FANTASM) and 2 warnings (PHRHIST_DISP, SPRIDEN_CHANGE_IND)
        assert errors >= 1, f"Expected at least 1 error (fantasm column), got {errors}"
        assert warnings >= 2, f"Expected at least 2 warnings (PHRHIST + SPRIDEN), got {warnings}"
        assert clickable >= 3, f"Expected at least 3 clickable items, got {clickable}"
        assert fix_buttons >= 2, f"Expected at least 2 fix buttons, got {fix_buttons}"

        #  History panel should now be visible with 1 entry
        after_panel_visible = page.locator('#sqlHistoryPanel').is_visible()
        history_count = page.locator('.sql-history-item').count()
        print(f"After validation, panel visible: {after_panel_visible}, history items: {history_count}")
        assert after_panel_visible, "History panel should be visible after first validation"
        assert history_count == 1, f"Expected 1 history entry, got {history_count}"

        #  Click on the first error (fantasm column) — should select the column in textarea
        page.locator('.sql-val-item.error.clickable').first.click()
        page.wait_for_timeout(200)
        sel_start = page.evaluate("document.getElementById('sqlInput').selectionStart")
        sel_end = page.evaluate("document.getElementById('sqlInput').selectionEnd")
        sel_text = page.evaluate("document.getElementById('sqlInput').value.slice("
                                  "document.getElementById('sqlInput').selectionStart,"
                                  "document.getElementById('sqlInput').selectionEnd)")
        print(f"After click-on-error: selection={sel_start}..{sel_end} text={sel_text!r}")
        assert 'PHRHIST_FANTASM' in (sel_text or '').upper(), \
            f"Expected selection to contain PHRHIST_FANTASM, got {sel_text!r}"

        #  Click on Copy fix button — assert the button changes label briefly
        fix_btn = page.locator('.sql-fix-btn').first
        fix_btn.click()
        page.wait_for_timeout(200)
        label = fix_btn.text_content() or ''
        print(f"After Copy-fix click: button label = {label!r}")
        assert 'Copied' in label, f"Expected fix button to show 'Copied' after click, got {label!r}"

        #  Reload — history should persist
        page.reload()
        page.wait_for_selector('#sqlInput', timeout=8000)
        persisted = page.locator('.sql-history-item').count()
        print(f"After reload, history items: {persisted}")
        assert persisted == 1, f"Expected history to persist 1 entry after reload, got {persisted}"

        #  Click the history entry — should fill the editor with the SQL
        page.locator('.sql-history-item').first.click()
        page.wait_for_timeout(300)
        editor_val = page.evaluate("document.getElementById('sqlInput').value")
        assert editor_val.strip() == TEST_SQL.strip(), \
            "Expected history click to repopulate the editor with the original SQL"
        print("History entry click restored the SQL into the editor.")

        #  Clean up storage
        page.evaluate("localStorage.removeItem('sql_explainer_history')")

        print()
        print("All interactivity assertions passed.")
        return 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except AssertionError as exc:
        print(f"!! ASSERTION FAILED: {exc}")
        sys.exit(1)

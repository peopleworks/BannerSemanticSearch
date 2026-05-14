"""
Smoke test for the target-dialect dropdown integration.

Verifies:
  1. Default target is 'oracle' — Oracle-only constructs produce ZERO
     dialect hints because they're valid on the Oracle target.
  2. Switching to PostgreSQL re-runs validation and surfaces Oracle→PG
     hints for the same SQL.
  3. The target preference persists in localStorage across reload.
  4. The dropdown widget gets the .pg accent class when PostgreSQL is
     selected.
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

#  Oracle-heavy SQL: clean on Oracle, full of red flags for PG.
ORACLE_SQL = """SELECT NVL(s.spriden_first_name, 'Unknown') AS fn,
       LISTAGG(p.phrhist_bdca_code, ',') WITHIN GROUP (ORDER BY p.phrhist_bdca_code) AS d,
       SYSDATE AS now_ts,
       ROWNUM AS rn
FROM   spriden s, phrhist p
WHERE  p.phrhist_pidm = s.spriden_pidm
   AND ROWNUM <= 50
"""


def explainer_open(page):
    page.goto(URL + '#/sql', wait_until='domcontentloaded')
    page.wait_for_selector('#sqlInput', timeout=8000)
    page.evaluate("try { localStorage.removeItem('sql_explainer_history'); } catch(e){}")
    page.locator('#sqlInput').fill(ORACLE_SQL)
    page.locator('#sqlExplainBtn').click()
    page.wait_for_selector('.sql-val-section', timeout=8000)


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={'width': 1600, 'height': 900})
        page = ctx.new_page()

        #  ===== Phase 1: default target = Oracle, no Oracle→PG hints =====
        page.goto(URL, wait_until='domcontentloaded')
        page.evaluate("try { localStorage.removeItem('sql_target_dialect_v1'); } catch(e){}")
        explainer_open(page)

        sel_default = page.locator('#targetDialectSel').input_value()
        pg_class_default = 'pg' in (page.get_attribute('#targetDialectWrap', 'class') or '')
        oracle_hints_default = page.evaluate(
            "Array.from(document.querySelectorAll('.sql-val-item.dialect .sql-val-msg')).map(e=>e.innerText).filter(t=>/NVL|LISTAGG|SYSDATE|ROWNUM/.test(t)).length"
        )
        dialect_count_default = page.locator('.sql-val-item.dialect').count()
        print(f"Default — target dropdown: {sel_default!r}, PG class: {pg_class_default}, total dialect hints: {dialect_count_default}, Oracle-specific hints: {oracle_hints_default}")
        assert sel_default == 'oracle', f"Default target should be 'oracle', got {sel_default!r}"
        assert not pg_class_default, "Wrap should not have .pg class when target is Oracle"
        assert oracle_hints_default == 0, f"Oracle-specific hints should NOT appear when target=Oracle, got {oracle_hints_default}"

        #  ===== Phase 2: switch to PostgreSQL, re-validation fires automatically =====
        page.locator('#targetDialectSel').select_option('postgresql')
        page.wait_for_timeout(400)
        sel_after = page.locator('#targetDialectSel').input_value()
        pg_class_after = 'pg' in (page.get_attribute('#targetDialectWrap', 'class') or '')
        dialect_count_after = page.locator('.sql-val-item.dialect').count()
        oracle_hints_after = page.evaluate(
            "Array.from(document.querySelectorAll('.sql-val-item.dialect .sql-val-msg')).map(e=>e.innerText).filter(t=>/NVL|LISTAGG|SYSDATE|ROWNUM/.test(t)).length"
        )
        print(f"After PG  — target dropdown: {sel_after!r}, PG class: {pg_class_after}, total dialect hints: {dialect_count_after}, Oracle-specific hints: {oracle_hints_after}")
        assert sel_after == 'postgresql', f"Target should be 'postgresql' after switch, got {sel_after!r}"
        assert pg_class_after, "Wrap should have .pg class when target is PostgreSQL"
        assert oracle_hints_after >= 4, f"Expected ≥4 Oracle→PG hints (NVL/LISTAGG/SYSDATE/ROWNUM), got {oracle_hints_after}"
        assert dialect_count_after > dialect_count_default, "PG target should produce MORE dialect hints than Oracle target"

        #  ===== Phase 3: reload, target persists =====
        page.reload()
        page.wait_for_selector('#sqlInput', timeout=8000)
        explainer_open(page)
        sel_reload = page.locator('#targetDialectSel').input_value()
        print(f"After reload — target dropdown: {sel_reload!r}")
        assert sel_reload == 'postgresql', "Target should persist as PostgreSQL across reload"

        #  Cleanup
        page.evaluate("try { localStorage.removeItem('sql_target_dialect_v1'); } catch(e){}")

        print()
        print(f"OK — target dialect dropdown gates Oracle→PG detector + persists.")
        return 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except AssertionError as exc:
        print(f"!! ASSERTION FAILED: {exc}")
        sys.exit(1)

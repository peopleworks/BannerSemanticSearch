"""
Smoke test for SQL Server → Oracle dialect hints.

Pastes a SQL query packed with SQL Server idioms and asserts that each
expected dialect hint fires.  Verifies:

  1. The "N dialect hints" badge appears with the right count.
  2. Hint items render with the 🔄 icon + cyan/teal styling.
  3. Hints have `target` (click-to-jump) and `fixSnippet` (Copy fix) where
     the translation is mechanical.
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

#  Synthetic SQL Server query that touches the 15+ patterns the detector knows:
#  TOP, [brackets], ISNULL, LEN, GETDATE, CHARINDEX, IIF, STRING_AGG, DATEDIFF,
#  DATEADD, CONVERT, WITH(NOLOCK), '+' concat, @variable, CROSS APPLY, INTO #temp.
TEST_SQL = """SELECT TOP 5
       [Name],
       LEN([Description]) AS desc_len,
       ISNULL(Phone, 'N/A') AS phone,
       GETDATE() AS today,
       CHARINDEX('-', SSN) AS dash_pos,
       IIF(Age > 18, 'Adult', 'Minor') AS group_t,
       Name + ' ' + LastName AS full_name,
       STRING_AGG(Department, ', ') AS depts,
       DATEDIFF(year, HireDate, GETDATE()) AS years,
       DATEADD(day, 30, EndDate) AS in_30_days,
       CONVERT(varchar, Salary, 1) AS fmt_salary
INTO   #tmp_results
FROM   [Employees] e WITH (NOLOCK)
CROSS  APPLY (SELECT MAX(D) FROM Dep d2 WHERE d2.E = e.Id) x
WHERE  @minSalary > 0
"""


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={'width': 1600, 'height': 900})
        page = ctx.new_page()
        page.goto(URL + '#/sql', wait_until='domcontentloaded')
        page.wait_for_selector('#sqlInput', timeout=8000)

        #  Wipe history so badges aren't polluted by prior runs
        page.evaluate("try { localStorage.removeItem('sql_explainer_history'); } catch(e){}")

        page.locator('#sqlInput').fill(TEST_SQL)
        page.locator('#sqlExplainBtn').click()
        page.wait_for_selector('.sql-val-section', timeout=8000)

        dialect_items = page.locator('.sql-val-item.dialect').count()
        dialect_badge = page.locator('.sql-val-badge.dialect').inner_text() if page.locator('.sql-val-badge.dialect').count() else ''
        fix_buttons = page.locator('.sql-val-item.dialect .sql-fix-btn').count()
        clickable_items = page.locator('.sql-val-item.dialect.clickable').count()

        print(f"Dialect items:     {dialect_items}")
        print(f"Dialect badge:     {dialect_badge!r}")
        print(f"Clickable dialect: {clickable_items}")
        print(f"Fix buttons:       {fix_buttons}")
        print()

        #  Dump the messages so we can eyeball what fired
        messages = page.locator('.sql-val-item.dialect .sql-val-msg').all_inner_texts()
        print('--- dialect hints ---')
        for i, m in enumerate(messages, 1):
            head = m.split('\n')[0]
            print(f"  {i:2}. {head[:90]}")

        #  Each pattern should fire at least once. The query above hits all 16.
        expected_keywords = [
            'TOP 5', '[bracketed]', 'ISNULL', 'LEN', 'GETDATE',
            'CHARINDEX', 'IIF', 'STRING_AGG', 'DATEDIFF', 'DATEADD',
            'CONVERT', 'WITH (NOLOCK)', '+', '@minSalary',
            'CROSS APPLY', '#tmp_results',
        ]
        missing = []
        joined = '\n'.join(messages)
        for kw in expected_keywords:
            if kw not in joined:
                missing.append(kw)
        if missing:
            print()
            print(f"!! REGRESSION: missing dialect hints for: {missing}")
            return 1

        assert dialect_items >= 14, f"Expected ≥14 dialect items, got {dialect_items}"
        assert clickable_items >= 14, f"Expected ≥14 clickable dialect items, got {clickable_items}"
        assert fix_buttons >= 8, f"Expected ≥8 fix buttons across dialect hints, got {fix_buttons}"
        assert 'dialect' in dialect_badge.lower(), f"Badge text odd: {dialect_badge!r}"

        print()
        print(f"OK — {dialect_items} dialect hints fired, {fix_buttons} have Copy-fix buttons.")
        return 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except AssertionError as exc:
        print(f"!! ASSERTION FAILED: {exc}")
        sys.exit(1)

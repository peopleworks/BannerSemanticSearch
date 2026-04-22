"""
Automated screenshot capture for the Banner Schema Search launch.

Opens docs/index.html in a headless Chromium, walks through the app's
hash-routed views + interactive flows (Banner Lego, Scorecard, Ask Banner,
SQL Explainer, Reports, Search), and writes the PNGs into docs/img/
using the filenames referenced by LAUNCH_PLAN.md.

Prerequisites (run once):
    pip install playwright
    playwright install chromium

Usage:
    python scripts/take_screenshots.py                # take all shots
    python scripts/take_screenshots.py lego scorecard # take just two by key

Each shot is wrapped in its own try/except so one failure doesn't kill
the batch. Output size, viewport, and forced theme are controlled per-shot.
"""

from __future__ import annotations
import os
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("Playwright not installed.  pip install playwright && playwright install chromium")
    sys.exit(1)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HTML = ROOT / 'docs' / 'index.html'
OUT_DIR = ROOT / 'docs' / 'img'
# file:// URL uses forward slashes and an extra slash after 'file:'
URL = 'file:///' + str(HTML).replace('\\', '/')

#  Default viewport for social-friendly 16:9 stills
DEFAULT_VIEWPORT = {'width': 1600, 'height': 900}


#  =====================================================================
#  INDIVIDUAL SHOTS — each returns the filename it wrote (relative to OUT_DIR)
#  =====================================================================

def shot_banner_lego(page):
    """Banner Lego with 'Student + Courses + Term' recipe loaded."""
    page.goto(URL + '#/builder', wait_until='domcontentloaded')
    page.wait_for_selector('.builder-grid', timeout=8000)
    #  Click the first recipe button (Student + Courses + Term)
    page.locator('.builder-recipe-btn').first.click()
    page.wait_for_selector('.builder-cblock', timeout=5000)
    #  Wait for the generated SQL to settle
    page.wait_for_function(
        "document.getElementById('builderSqlPre') && "
        "document.getElementById('builderSqlPre').textContent.includes('spriden')",
        timeout=5000
    )
    time.sleep(0.4)
    return 'banner-lego.png'


def shot_scorecard(page):
    """Security Posture Scorecard populated with a mixed-status dummy row."""
    page.goto(URL + '#/scorecard', wait_until='domcontentloaded')
    page.wait_for_selector('.scorecard-paste-area', timeout=8000)

    #  Dummy row crafted to produce mixed greens/yellows/reds
    dummy = (
        "total_accounts\tusers_with_access\ttotal_effective_grants\t"
        "dormant_accounts\tterminated_with_access\tusers_bypassing_classes\t"
        "super_users\tpii_broad_users\tviolations_30d\tunused_classes\t"
        "legacy_gurucls_rows\taccess_changes_30d\tsnapshot_taken_at\n"
        "5234\t842\t418562\t23\t1\t18\t12\t8\t67\t42\t7582\t145\t2026-04-22 11:30"
    )
    page.locator('.scorecard-paste-area').fill(dummy)
    #  Click the "Update dashboard" button
    page.get_by_text('Update dashboard').click()
    page.wait_for_selector('.scorecard-gauge.status-red', timeout=5000)
    time.sleep(0.3)
    return 'scorecard.png'


def shot_ask_banner(page):
    """Ask Banner card generated for 'access to SHAINST'."""
    page.goto(URL, wait_until='domcontentloaded')
    page.wait_for_selector('#searchInput', timeout=5000)
    #  Trigger via hash so we don't have to wait for debounce
    page.goto(URL + '#/search/access%20to%20SHAINST', wait_until='domcontentloaded')
    page.wait_for_selector('.intent-card', timeout=8000)
    #  Make sure the SQL block has rendered
    page.wait_for_selector('.intent-sql', timeout=5000)
    time.sleep(0.3)
    return 'ask-banner.png'


def shot_module_grid(page):
    """SR013 module overview — the 8-card Ellucian module reference grid."""
    page.goto(URL + '#/search/list%20banner%20modules', wait_until='domcontentloaded')
    page.wait_for_selector('.module-grid', timeout=8000)
    #  Scroll to the grid so it's the focal point
    page.evaluate(
        "document.querySelector('.module-grid').scrollIntoView({block: 'center'})"
    )
    time.sleep(0.4)
    return 'module-grid.png'


def shot_sql_explainer(page):
    """SQL Explainer catching a deliberately broken query."""
    page.goto(URL + '#/sql', wait_until='domcontentloaded')
    page.wait_for_selector('#sqlInput, textarea', timeout=5000)
    #  The SQL textarea — fill with a query that references a phantom column
    bad_sql = (
        "-- A query with a phantom column + missing WHERE guard\n"
        "SELECT x.phantasm_col, x.ftvvend_start_date\n"
        "FROM   ftvvend x\n"
        "WHERE  x.fake_filter = 1;"
    )
    #  Try common selectors for the SQL input
    for sel in ['#sqlInput', '#sqlText', 'textarea.sql-input', 'textarea']:
        try:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.fill(bad_sql)
                break
        except Exception:
            continue
    #  Click the Explain button
    for sel in ['#sqlExplainBtn', 'button:has-text("Explain")',
                'button:has-text("Validate")']:
        try:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.click()
                break
        except Exception:
            continue
    #  Wait for some validation output to appear
    try:
        page.wait_for_selector('.sql-warning, .sql-issue, .did-you-mean, '
                               '.sql-result, .sql-findings', timeout=6000)
    except PWTimeout:
        pass  # still take the shot so we can see what DID render
    time.sleep(0.5)
    return 'sql-explainer.png'


def shot_search_synonyms(page):
    """Search results for 'employee hire date' showing synonym-expansion chips."""
    page.goto(URL + '#/search/employee%20hire%20date', wait_until='domcontentloaded')
    page.wait_for_selector('.search-result, .table-result, .term-builder, .result-group',
                            timeout=8000)
    time.sleep(0.5)
    return 'search-synonyms.png'


def shot_reports_index(page):
    """The full reports index page — 14 SR0XX cards grouped by category."""
    page.goto(URL + '#/reports', wait_until='domcontentloaded')
    page.wait_for_selector('.report-card', timeout=8000)
    time.sleep(0.4)
    return 'reports-index.png'


#  =====================================================================
#  DRIVER
#  =====================================================================

SHOTS = {
    'lego':        (shot_banner_lego,     {'width': 1600, 'height': 1000}),
    'scorecard':   (shot_scorecard,       {'width': 1600, 'height': 1100}),
    'ask-banner':  (shot_ask_banner,      {'width': 1600, 'height': 1000}),
    'module-grid': (shot_module_grid,     {'width': 1600, 'height': 1100}),
    'sql-explain': (shot_sql_explainer,   {'width': 1600, 'height': 1000}),
    'search':      (shot_search_synonyms, {'width': 1600, 'height': 1000}),
    'reports':     (shot_reports_index,   {'width': 1600, 'height': 1100}),
}


def take_shot(browser, key, fn, viewport, out_dir):
    """Run a single shot. Returns True on success."""
    context = browser.new_context(
        viewport=viewport,
        color_scheme='light',            # force light mode for bright social feeds
        device_scale_factor=2,           # HiDPI / retina crisp output
    )
    #  Pre-set localStorage so the app picks up 'light' without flash
    context.add_init_script(
        "try { localStorage.setItem('theme', 'light'); } catch(e) {}"
    )
    page = context.new_page()
    page.on('console', lambda m: None)   # suppress console noise
    try:
        filename = fn(page)
        path = out_dir / filename
        page.screenshot(path=str(path), full_page=False)
        size_kb = path.stat().st_size / 1024
        print(f"  [OK]   {key:12} -> {filename}  ({viewport['width']}x{viewport['height']}, {size_kb:.0f} KB)")
        return True
    except Exception as e:
        print(f"  [FAIL] {key:12} -> {e}")
        return False
    finally:
        context.close()


def main():
    if not HTML.is_file():
        print(f"docs/index.html not found. Run `python build.py` first.")
        sys.exit(1)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    requested = sys.argv[1:]
    if requested:
        todo = [k for k in requested if k in SHOTS]
        unknown = [k for k in requested if k not in SHOTS]
        if unknown:
            print(f"Unknown shot key(s): {unknown}")
            print(f"Valid keys: {list(SHOTS.keys())}")
            sys.exit(1)
    else:
        todo = list(SHOTS.keys())

    print(f"Taking {len(todo)} screenshot(s) from {HTML.name} -> {OUT_DIR.relative_to(ROOT)}/")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            ok_count = 0
            for key in todo:
                fn, viewport = SHOTS[key]
                if take_shot(browser, key, fn, viewport, OUT_DIR):
                    ok_count += 1
            print(f"\nDone. {ok_count}/{len(todo)} succeeded.")
            return 0 if ok_count == len(todo) else 2
        finally:
            browser.close()


if __name__ == '__main__':
    sys.exit(main())

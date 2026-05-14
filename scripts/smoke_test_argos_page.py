"""
Smoke test for the Argos cheatsheet page (#/argos).

Verifies that the three reference sections render with the right cards
and rows so future template tweaks don't accidentally drop content.
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


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={'width': 1600, 'height': 1100})
        page = ctx.new_page()
        page.goto(URL + '#/argos', wait_until='domcontentloaded')

        page.wait_for_selector('.argos-intro', timeout=8000)

        cards = page.locator('.argos-prefix-grid .argos-card').count()
        ref_tables = page.locator('.argos-ref-table').count()
        ref_rows = page.locator('.argos-ref-table tbody tr').count()
        prefixes = [t.strip() for t in page.locator('.argos-card-prefix').all_inner_texts()]
        sections = page.locator('.argos-section h3').all_inner_texts()
        pattern_cards = page.locator('.argos-pattern').count()
        pattern_copy_btns = page.locator('.argos-pattern .sql-fix-btn').count()
        pattern_titles = page.locator('.argos-pattern-title').all_inner_texts()

        print(f"Prefix cards:        {cards}")
        print(f"Prefixes:            {prefixes}")
        print(f"Reference tables:    {ref_tables}")
        print(f"Total ref rows:      {ref_rows}")
        print(f"Sections:            {sections}")
        print(f"Pattern cards:       {pattern_cards}")
        print(f"Pattern titles:      {pattern_titles}")
        print(f"Copy buttons:        {pattern_copy_btns}")

        assert cards == 3, f"Expected 3 prefix cards, got {cards}"
        assert ':main_*' in prefixes, "Expected :main_* card"
        assert ':lcl_*'  in prefixes, "Expected :lcl_* card"
        assert ':dbn_*'  in prefixes, "Expected :dbn_* card"
        assert ref_tables == 2, f"Expected 2 reference tables (accessors + widgets), got {ref_tables}"
        assert ref_rows >= 12, f"Expected ≥12 ref rows across both tables, got {ref_rows}"
        assert pattern_cards >= 7, f"Expected ≥7 pattern cards, got {pattern_cards}"
        assert pattern_copy_btns == pattern_cards, \
            f"Expected one Copy button per pattern card ({pattern_cards}), got {pattern_copy_btns}"

        #  Section 5: Banner Cloud reality check — Oracle ↔ PostgreSQL table
        cloud_rows = page.locator('.cloud-diff-table tbody tr').count()
        cloud_callout = page.locator('.argos-cloud-callout').count()
        section_count = page.locator('.argos-section').count()
        print(f"Cloud-reality table rows: {cloud_rows}, callout visible: {bool(cloud_callout)}, total argos sections: {section_count}")
        assert cloud_rows >= 16, f"Expected ≥16 Oracle↔PG mapping rows, got {cloud_rows}"
        assert cloud_callout >= 1, "Expected the Banner Cloud heads-up callout"
        assert section_count >= 5, f"Expected 5 sections on the Argos page (prefixes/accessors/widgets/patterns/cloud), got {section_count}"

        #  Click one Copy button and assert the label flips to '✓ Copied'
        first_copy = page.locator('.argos-pattern .sql-fix-btn').first
        first_copy.click()
        page.wait_for_timeout(200)
        copy_label = first_copy.text_content() or ''
        assert 'Copied' in copy_label, f"Expected Copy button to flip to Copied, got {copy_label!r}"
        print(f"Copy button click confirms label flip: {copy_label!r}")

        #  Click the "Open the SQL Explainer →" link, confirm we navigate there
        page.locator('a[href="#/sql"]').first.click()
        page.wait_for_selector('#sqlInput', timeout=5000)
        print("Link to SQL Explainer works.")

        print()
        print("OK — Argos cheatsheet page renders all 3 sections with full content.")
        return 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except AssertionError as exc:
        print(f"!! ASSERTION FAILED: {exc}")
        sys.exit(1)

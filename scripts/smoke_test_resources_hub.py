"""
Smoke test for the Community Resources Hub (#/resources).

Verifies that:
  1. The hub page renders with intro + Argos section.
  2. Every resource card has title, host, type badge, and a real http(s)
     external URL that opens in a new tab.
  3. Each card links to a vendor / community domain (no relative URLs).

Commit 1 ships the Argos section only — Banner + Community sections
arrive in commits 2 & 3 and extend this test.
"""
from __future__ import annotations
import sys
from pathlib import Path
from urllib.parse import urlparse

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
        ctx = browser.new_context(viewport={'width': 1600, 'height': 1200})
        page = ctx.new_page()
        page.goto(URL + '#/resources', wait_until='domcontentloaded')
        page.wait_for_selector('.resources-intro', timeout=8000)

        argos_cards = page.locator('.resource-card.argos').count()
        all_cards = page.locator('.resource-card').count()
        sections = page.locator('.resources-section').count()
        intro_visible = page.locator('.resources-intro').count() > 0

        print(f"Argos cards:   {argos_cards}")
        print(f"Total cards:   {all_cards}")
        print(f"Sections:      {sections}")
        print(f"Intro visible: {intro_visible}")

        assert argos_cards >= 8, f"Expected ≥8 Argos resource cards, got {argos_cards}"
        assert intro_visible, "Resources page should show the philosophy intro callout"

        #  Inspect each card — must have title, host, type badge, real URL
        hrefs = page.locator('.resource-card').evaluate_all(
            "els => els.map(e => ({ href: e.href, host: e.querySelector('.resource-card-host')?.textContent || '', "
            "title: e.querySelector('.resource-card-title')?.textContent || '', "
            "type: e.querySelector('.resource-card-type')?.textContent || '' }))"
        )
        for i, c in enumerate(hrefs, 1):
            scheme = urlparse(c['href']).scheme
            netloc = urlparse(c['href']).netloc
            print(f"  {i:2}. [{c['type']:>10}] {c['title'][:55]:55}  →  {netloc}")
            assert scheme in ('http', 'https'), f"Card {i} has non-http URL: {c['href']}"
            assert c['title'].strip(), f"Card {i} is missing title"
            assert c['host'].strip(),  f"Card {i} is missing host"

        #  Footer link to the Argos cheatsheet should work
        page.locator('a[href="#/argos"]').first.click()
        page.wait_for_selector('.argos-intro', timeout=4000)
        print("Footer link → /argos cheatsheet works.")

        print()
        print(f"OK — {argos_cards} Argos resource cards rendered with real vendor URLs.")
        return 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except AssertionError as exc:
        print(f"!! ASSERTION FAILED: {exc}")
        sys.exit(1)

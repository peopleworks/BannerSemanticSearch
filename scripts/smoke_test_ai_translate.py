"""
Smoke test for the "🔍 Translate from SQL Server" button + the AI status chip.

Verifies:
  1. AI status chip in the header shows 'AI off' (.off class) when disabled.
  2. Enabling AI flips the chip to .on with the provider name visible.
  3. Translate button only renders when AI is enabled.
  4. Clicking Translate opens the same panel infrastructure as Suggest fix
     and re-enables the button when the call settles (even on error).
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
        ctx = browser.new_context(viewport={'width': 1600, 'height': 900})
        page = ctx.new_page()

        #  ===== Phase 1: AI disabled — chip shows off, no Translate button =====
        page.goto(URL, wait_until='domcontentloaded')
        page.evaluate("try { localStorage.removeItem('ai_settings_v1'); } catch(e){}")
        page.reload()
        page.wait_for_selector('#aiChip', timeout=8000)
        chip_class_off = page.get_attribute('#aiChip', 'class') or ''
        chip_label_off = page.locator('#aiChipLabel').inner_text()
        print(f"AI disabled — chip class: {chip_class_off!r}, label: {chip_label_off!r}")
        assert 'off' in chip_class_off and 'on' not in chip_class_off, "Chip should show OFF state"
        assert 'off' in chip_label_off.lower(), "Chip label should say 'AI off'"

        page.goto(URL + '#/sql', wait_until='domcontentloaded')
        page.wait_for_selector('#sqlInput', timeout=8000)
        translate_off = page.locator('#aiTranslateBtn').count()
        print(f"Translate button visible: {bool(translate_off)} (expected False)")
        assert translate_off == 0, "Translate button should be hidden when AI disabled"

        #  ===== Phase 2: enable AI, chip flips to ON =====
        page.evaluate("""
            localStorage.setItem('ai_settings_v1', JSON.stringify({
                enabled: true,
                provider: 'anthropic',
                providers: {
                    anthropic: { apiKey: 'sk-ant-FAKE', model: 'claude-haiku-4-5-20251001' },
                    openai:    { apiKey: '', model: 'gpt-4o-mini' },
                    ollama:    { baseUrl: 'http://localhost:11434', model: 'llama3.1' }
                },
                redaction: 'standard',
                stream: false,
                stats: { lastTest: null, lastTestStatus: null, callsToday: 0, lastCallDate: null }
            }));
        """)
        page.reload()
        page.wait_for_selector('#aiChip', timeout=8000)
        chip_class_on = page.get_attribute('#aiChip', 'class') or ''
        chip_label_on = page.locator('#aiChipLabel').inner_text()
        print(f"AI enabled  — chip class: {chip_class_on!r}, label: {chip_label_on!r}")
        assert 'on' in chip_class_on, "Chip should show ON state"
        assert 'Anthropic' in chip_label_on, "Chip label should mention provider"

        #  ===== Phase 3: Translate button visible, click triggers panel =====
        page.goto(URL + '#/sql', wait_until='domcontentloaded')
        page.wait_for_selector('#aiTranslateBtn', timeout=8000)
        print("Translate button rendered — visible.")

        page.locator('#sqlInput').fill("SELECT TOP 5 ISNULL(name, 'unknown') FROM [Employees]")
        page.locator('#aiTranslateBtn').click()
        page.wait_for_selector('.ai-suggest-panel', timeout=4000)
        try:
            page.wait_for_function(
                "!document.getElementById('aiTranslateBtn').disabled",
                timeout=15000
            )
        except Exception:
            pass

        panel_count = page.locator('.ai-suggest-panel').count()
        title_text = page.locator('.ai-suggest-title').inner_text()
        btn_re_enabled = not page.evaluate("document.getElementById('aiTranslateBtn').disabled")
        print(f"After click — panel: {panel_count}, title: {title_text!r}, btn re-enabled: {btn_re_enabled}")
        assert panel_count == 1, "Translate panel should appear"
        assert 'SQL Server' in title_text and 'Oracle' in title_text, "Title should reflect translation"
        assert btn_re_enabled, "Translate button should re-enable when call settles"

        #  ===== Phase 4: chip click navigates to settings =====
        page.goto(URL, wait_until='domcontentloaded')
        page.wait_for_selector('#aiChip', timeout=8000)
        page.locator('#aiChip').click()
        page.wait_for_selector('.settings-disclaimer', timeout=4000)
        url_after = page.url
        print(f"Chip click navigated to: {url_after.split('#')[-1] if '#' in url_after else '(no hash)'}")
        assert '/settings' in url_after, "Chip click should navigate to #/settings"

        #  Cleanup
        page.evaluate("try { localStorage.removeItem('ai_settings_v1'); } catch(e){}")

        print()
        print("OK — AI chip reflects state, Translate button gates correctly, click flow works.")
        return 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except AssertionError as exc:
        print(f"!! ASSERTION FAILED: {exc}")
        sys.exit(1)

"""
Smoke test for the "✨ Explain in depth" button on validation items.

Verifies:
  1. When AI is disabled (default), NO ai-explain-btn elements appear in
     the validation output — feature stays hidden.
  2. When AI is enabled, an ai-explain-btn appears on every error, warning,
     and dialect hint (in addition to Copy-fix where applicable).
  3. The button is wired (clicking triggers either the AI call or, in this
     test environment without a real key, a graceful error in the panel).
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

#  Same SQL the interactivity test uses — guaranteed to produce errors + warnings.
TEST_SQL = """SELECT h.PHRHIST_PIDM, h.PHRHIST_GROSS, s.SPRIDEN_LAST_NAME, h.PHRHIST_FANTASM
FROM   PHRHIST h
JOIN   SPRIDEN s ON s.SPRIDEN_PIDM = h.PHRHIST_PIDM
WHERE  h.PHRHIST_YEAR = 2025
"""


def open_explainer(page):
    page.goto(URL + '#/sql', wait_until='domcontentloaded')
    page.wait_for_selector('#sqlInput', timeout=8000)
    page.evaluate("try { localStorage.removeItem('sql_explainer_history'); } catch(e){}")
    page.locator('#sqlInput').fill(TEST_SQL)
    page.locator('#sqlExplainBtn').click()
    page.wait_for_selector('.sql-val-section', timeout=8000)


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={'width': 1600, 'height': 900})
        page = ctx.new_page()

        #  ===== Phase 1: AI disabled =====
        page.goto(URL, wait_until='domcontentloaded')
        page.evaluate("try { localStorage.removeItem('ai_settings_v1'); } catch(e){}")
        open_explainer(page)
        ai_btns_off = page.locator('.ai-explain-btn').count()
        val_items_off = page.locator('.sql-val-item').count()
        print(f"AI disabled — validation items: {val_items_off}, ai-explain-btn count: {ai_btns_off}")
        assert ai_btns_off == 0, f"AI buttons should NOT appear when AI is disabled, got {ai_btns_off}"

        #  ===== Phase 2: enable AI via Settings, re-validate =====
        page.evaluate("""
            localStorage.setItem('ai_settings_v1', JSON.stringify({
                enabled: true,
                provider: 'anthropic',
                providers: {
                    anthropic: { apiKey: 'sk-ant-FAKE-FOR-TESTING', model: 'claude-haiku-4-5-20251001' },
                    openai:    { apiKey: '', model: 'gpt-4o-mini' },
                    ollama:    { baseUrl: 'http://localhost:11434', model: 'llama3.1' }
                },
                redaction: 'standard',
                stream: false,
                stats: { lastTest: null, lastTestStatus: null, callsToday: 0, lastCallDate: null }
            }));
        """)
        page.reload()
        open_explainer(page)
        ai_btns_on = page.locator('.ai-explain-btn').count()
        val_items_on = page.locator('.sql-val-item').count()
        items_with_target = page.locator('.sql-val-item.clickable').count()
        print(f"AI enabled  — validation items: {val_items_on}, clickable: {items_with_target}, ai-explain-btn count: {ai_btns_on}")
        assert ai_btns_on >= items_with_target, \
            f"Expected at least one AI button per clickable validation item ({items_with_target}), got {ai_btns_on}"

        #  ===== Phase 3: click an AI button, expect graceful error panel =====
        first_btn = page.locator('.ai-explain-btn').first
        first_btn.click()
        #  Without a real key the Anthropic call will fail — we want the panel
        #  to appear AND the button to re-enable when the error settles.
        page.wait_for_selector('.ai-response', timeout=4000)
        #  Poll up to 15s for the button to re-enable (network call to api.anthropic.com
        #  with a fake key takes the full TLS handshake + 401 round-trip).
        try:
            page.wait_for_function(
                "!document.querySelector('.ai-explain-btn').disabled",
                timeout=15000
            )
        except Exception:
            pass
        panel_visible = page.locator('.ai-response').count() > 0
        has_error_class = page.evaluate(
            "Array.from(document.querySelectorAll('.ai-response')).some(p => p.classList.contains('error'))"
        )
        btn_disabled = page.evaluate("document.querySelector('.ai-explain-btn').disabled")
        print(f"After click — panel visible: {panel_visible}, panel has error class: {has_error_class}, btn re-enabled: {not btn_disabled}")
        assert panel_visible, "AI response panel should appear after click"
        assert not btn_disabled, "Button should re-enable after the call settles (success or error)"
        assert has_error_class, "Without a real API key the panel should land in the error state"

        #  ===== Phase 4: close button works =====
        close_btn = page.locator('.ai-response-close').first
        close_btn.click()
        page.wait_for_timeout(150)
        remaining = page.locator('.ai-response').count()
        print(f"After close click — remaining panels: {remaining}")
        assert remaining == 0, "Close button should remove the panel"

        #  Cleanup
        page.evaluate("try { localStorage.removeItem('ai_settings_v1'); } catch(e){}")
        page.evaluate("try { localStorage.removeItem('sql_explainer_history'); } catch(e){}")

        print()
        print("OK — Explain-in-depth button respects toggle, wires into AI pipeline, fails gracefully.")
        return 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except AssertionError as exc:
        print(f"!! ASSERTION FAILED: {exc}")
        sys.exit(1)

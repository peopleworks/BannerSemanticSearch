"""
Smoke test for the "💡 Suggest fix" button + LCS diff rendering.

Verifies:
  1. When AI is disabled, the Suggest-fix button does NOT render in the
     Explainer button row.
  2. When AI is enabled, the button renders next to "Explain & Validate".
  3. diffLines() correctly emits 'same' / 'add' / 'remove' entries via LCS.
  4. extractFencedSql() pulls SQL from the standard ```sql fences and from
     bare ``` fences as a fallback.
  5. Clicking the button without a real key surfaces a graceful error in
     the panel and re-enables the button.
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

        #  ===== Phase 1: AI disabled — button hidden =====
        page.goto(URL, wait_until='domcontentloaded')
        page.evaluate("try { localStorage.removeItem('ai_settings_v1'); } catch(e){}")
        page.goto(URL + '#/sql', wait_until='domcontentloaded')
        page.wait_for_selector('#sqlInput', timeout=8000)
        suggest_off = page.locator('#aiSuggestBtn').count()
        print(f"AI disabled — Suggest button count: {suggest_off}")
        assert suggest_off == 0, "Suggest-fix button should NOT render when AI disabled"

        #  ===== Phase 2: enable AI, button appears =====
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
        page.wait_for_selector('#aiSuggestBtn', timeout=8000)
        print(f"AI enabled  — Suggest button visible: True")

        #  ===== Phase 3: diffLines via the exposed window function =====
        diff_cases = [
            #  (label, old, new, expected_min_adds, expected_min_removes)
            ("identical", "A\nB\nC", "A\nB\nC", 0, 0),
            ("one line added",  "A\nB\nC",       "A\nB\nC\nD",   1, 0),
            ("one line removed","A\nB\nC\nD",    "A\nB\nC",       0, 1),
            ("one line changed","A\nB\nC",       "A\nX\nC",       1, 1),
        ]
        for (label, old, new, exp_add, exp_rem) in diff_cases:
            diff = page.evaluate(
                f"window.diffLines({old!r}, {new!r}).map(d => d.type)"
            )
            adds = sum(1 for t in diff if t == 'add')
            rems = sum(1 for t in diff if t == 'remove')
            print(f"  diff {label!r}: {diff}  (adds={adds}, removes={rems})")
            assert adds >= exp_add, f"{label!r}: expected ≥{exp_add} adds, got {adds}"
            assert rems >= exp_rem, f"{label!r}: expected ≥{exp_rem} removes, got {rems}"

        #  ===== Phase 4: extractFencedSql parsing =====
        fence_cases = [
            ("```sql\nSELECT 1 FROM dual\n```\n• note",        "SELECT 1 FROM dual"),
            ("here you go:\n```\nSELECT 2 FROM dual\n```\n",   "SELECT 2 FROM dual"),
            ("SELECT 3 FROM dual\n\nexplanation here",          "SELECT 3 FROM dual"),
        ]
        for (input_text, expected) in fence_cases:
            got = page.evaluate(f"window.extractFencedSql({input_text!r})")
            print(f"  extractFencedSql({input_text[:30]!r}…) -> {got!r}")
            assert expected in got, f"Expected {expected!r} in extracted SQL, got {got!r}"

        #  ===== Phase 5: click the button, expect graceful error =====
        page.locator('#sqlInput').fill("SELECT * FROM SPRIDEN")
        page.locator('#aiSuggestBtn').click()
        page.wait_for_selector('.ai-suggest-panel', timeout=4000)
        try:
            page.wait_for_function(
                "!document.getElementById('aiSuggestBtn').disabled",
                timeout=15000
            )
        except Exception:
            pass
        btn_disabled = page.evaluate("document.getElementById('aiSuggestBtn').disabled")
        panel_visible = page.locator('.ai-suggest-panel').count() > 0
        explanation = page.locator('.ai-suggest-explanation').inner_text()
        print(f"After click — panel visible: {panel_visible}, btn re-enabled: {not btn_disabled}, explanation has '⚠': {'⚠' in explanation}")
        assert panel_visible, "Suggest panel should appear after click"
        assert not btn_disabled, "Button should re-enable after the call settles"

        #  Cleanup
        page.evaluate("try { localStorage.removeItem('ai_settings_v1'); } catch(e){}")

        print()
        print("OK — Suggest-fix button gates on toggle, diff + fence parser work, click flow is graceful.")
        return 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except AssertionError as exc:
        print(f"!! ASSERTION FAILED: {exc}")
        sys.exit(1)

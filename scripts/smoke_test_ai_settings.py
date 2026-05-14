"""
Smoke test for AI Settings page (#/settings).

Verifies that:
  1. The page renders with the master toggle OFF by default and the
     configuration panel collapsed (display:none).
  2. Toggling enables the panel and persists to localStorage.
  3. Switching provider rebuilds the model dropdown and updates the
     key-input label/placeholder.
  4. Save persists all fields; reload restores them.
  5. The privacy disclaimer is prominent.
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
        ctx = browser.new_context(viewport={'width': 1400, 'height': 1000})
        page = ctx.new_page()
        page.goto(URL + '#/settings', wait_until='domcontentloaded')

        #  Wipe any prior settings so the test starts deterministic
        page.evaluate("try { localStorage.removeItem('ai_settings_v1'); } catch(e){}")
        page.reload()
        page.wait_for_selector('.settings-disclaimer', timeout=8000)

        #  1. Initial state — toggle OFF, panel hidden
        cfg_panel_visible = page.locator('#aiCfgPanel').is_visible()
        toggle_on = page.evaluate("document.querySelector('.settings-toggle').classList.contains('on')")
        state_text = page.locator('#aiToggleState').inner_text()
        disclaimer_visible = page.locator('.settings-disclaimer').is_visible()
        print(f"Initial: toggle={'ON' if toggle_on else 'OFF'} ({state_text}), panel visible={cfg_panel_visible}, disclaimer visible={disclaimer_visible}")
        assert not toggle_on, "Toggle should default OFF"
        assert not cfg_panel_visible, "Config panel should be collapsed when AI disabled"
        assert disclaimer_visible, "Privacy disclaimer must always be visible"

        #  2. Click toggle — panel expands, state persists
        page.locator('.settings-toggle').click()
        page.wait_for_timeout(150)
        cfg_panel_visible = page.locator('#aiCfgPanel').is_visible()
        toggle_on = page.evaluate("document.querySelector('.settings-toggle').classList.contains('on')")
        stored = page.evaluate("JSON.parse(localStorage.getItem('ai_settings_v1') || '{}')")
        print(f"After toggle click: ON={toggle_on}, panel visible={cfg_panel_visible}, stored.enabled={stored.get('enabled')}")
        assert toggle_on, "Toggle should be ON after click"
        assert cfg_panel_visible, "Config panel should expand when AI enabled"
        assert stored.get('enabled') is True, "Storage should reflect enabled=true"

        #  3. Verify default model dropdown options for Anthropic
        anthropic_models = page.locator('#aiModel option').all_inner_texts()
        print(f"Anthropic models: {[m.split(' · ')[0] for m in anthropic_models]}")
        assert any('Claude Haiku 4.5' in m for m in anthropic_models), "Expected Haiku in model list"
        assert any('Claude Sonnet 4.6' in m for m in anthropic_models), "Expected Sonnet in model list"

        #  4. Switch provider to Ollama, verify key input changes to text + URL
        page.locator('#aiProvider').select_option('ollama')
        page.wait_for_timeout(150)
        key_label = page.locator('#aiKeyLabel').inner_text()
        key_input_type = page.evaluate("document.getElementById('aiApiKey').type")
        key_input_val = page.evaluate("document.getElementById('aiApiKey').value")
        ollama_models = page.locator('#aiModel option').all_inner_texts()
        print(f"After provider=Ollama: label={key_label!r}, input type={key_input_type}, value={key_input_val!r}")
        print(f"Ollama models: {[m.split(' · ')[0] for m in ollama_models]}")
        assert 'Ollama' in key_label or 'URL' in key_label, "Label should switch to URL for Ollama"
        assert key_input_type == 'text', "Ollama URL should not be a password field"
        assert 'localhost:11434' in key_input_val, "Should pre-fill default Ollama URL"
        assert any('Llama 3.1' in m for m in ollama_models), "Expected Ollama models"

        #  5. Switch to OpenAI, set a dummy key, save, reload, verify persistence
        page.locator('#aiProvider').select_option('openai')
        page.wait_for_timeout(150)
        page.locator('#aiApiKey').fill('sk-proj-dummy-test-key-not-real')
        page.locator('#aiSaveBtn').click()
        page.wait_for_timeout(200)

        page.reload()
        page.wait_for_selector('.settings-disclaimer', timeout=8000)
        prov_val = page.locator('#aiProvider').input_value()
        key_val = page.locator('#aiApiKey').input_value()
        print(f"After reload: provider={prov_val}, key={key_val[:15]!r}...")
        assert prov_val == 'openai', f"Expected provider=openai after reload, got {prov_val}"
        assert key_val == 'sk-proj-dummy-test-key-not-real', "Key should round-trip through localStorage"

        #  6. Clean up
        page.evaluate("try { localStorage.removeItem('ai_settings_v1'); } catch(e){}")

        print()
        print("OK — settings page renders, toggle works, persistence verified across providers.")
        return 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except AssertionError as exc:
        print(f"!! ASSERTION FAILED: {exc}")
        sys.exit(1)

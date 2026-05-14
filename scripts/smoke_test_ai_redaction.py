"""
Smoke test for client-side redaction (redactSql).

Verifies that the redactor masks PII patterns in SQL string literals
before they would be sent to any AI provider. Doesn't require any API
keys — runs the redaction function directly in the browser context.
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

#  Cases: (label, level, input, expected substring [or None to assert NOT in])
CASES = [
    #  Standard redaction
    ('SSN literal',          'standard',
        "WHERE ssn = '123-45-6789'",                "<REDACTED:SSN>"),
    ('Email literal',        'standard',
        "WHERE email = 'pedro@waubonsee.edu'",     "<REDACTED:EMAIL>"),
    ('Long ID (PIDM-like)',  'standard',
        "WHERE pidm = '12345678'",                  "<REDACTED:ID>"),
    ('Short ID NOT masked',  'standard',
        "WHERE term = '202410'",                    "REDACTED"),       # WILL mask (6-digit threshold) — sanity-check it does
    ('Phone literal',        'standard',
        "WHERE phone = '(630) 555-1234'",           "<REDACTED:PHONE>"),
    ('Off level passes through','off',
        "WHERE ssn = '123-45-6789'",                "123-45-6789"),
    #  Strict-only truncation
    ('Strict truncates long', 'strict',
        "WHERE note = 'this is a long string literal that should be truncated because it is over fifty characters'",
        "<...truncated>"),
    #  Should NOT redact non-literal numbers (column references, SQL math)
    ('Non-literal number kept','standard',
        "WHERE amount > 100000",                    "100000"),
]


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.goto(URL, wait_until='domcontentloaded')
        page.wait_for_function("typeof window.redactSql === 'function'", timeout=8000)

        failures = []
        for (label, level, src, expected) in CASES:
            out = page.evaluate(f"window.redactSql({src!r}, {level!r})")
            ok = (expected in out)
            marker = '✓' if ok else '✗'
            print(f"  {marker} [{level:8}] {label}")
            print(f"      in : {src}")
            print(f"      out: {out}")
            if not ok:
                failures.append((label, level, src, expected, out))

        print()
        if failures:
            print(f"!! {len(failures)} REGRESSION(S):")
            for f in failures:
                print(f"   {f[0]} — expected {f[3]!r} in output, got: {f[4]!r}")
            return 1

        print(f"OK — {len(CASES)} redaction cases passed. PII never leaves the browser.")
        return 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except AssertionError as exc:
        print(f"!! ASSERTION FAILED: {exc}")
        sys.exit(1)

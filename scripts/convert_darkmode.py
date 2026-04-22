"""
One-shot transformer: converts every
    @media (prefers-color-scheme: dark) { ... rules ... }
block in templates/index.html into an equivalent class-based form:
    html.dark RULES
so that JavaScript can control dark mode by toggling the `dark` class on <html>.

Safe to run multiple times — idempotent (skips already-transformed blocks).
"""

import os
import re
import sys

HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
TEMPLATE = os.path.join(ROOT, 'templates', 'index.html')

MEDIA_MARK = '@media (prefers-color-scheme: dark)'


def find_matching_brace(text, open_idx):
    """Given the index of '{' return index of matching '}'. -1 if not balanced."""
    depth = 0
    i = open_idx
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def split_top_level_rules(body):
    """Given the inside of a media block, yield (selector_str, block_including_braces).
    Comments inline are preserved by treating them as whitespace for structure."""
    i = 0
    n = len(body)
    out = []
    while i < n:
        # skip leading whitespace
        while i < n and body[i] in ' \t\n\r':
            i += 1
        if i >= n:
            break
        # find the next { at depth 0
        j = i
        while j < n and body[j] != '{':
            j += 1
        if j >= n:
            # leftover garbage
            break
        sel = body[i:j].strip()
        end = find_matching_brace(body, j)
        if end == -1:
            raise ValueError("Unbalanced braces in media block")
        rule_body = body[j:end + 1]  # includes { }
        out.append((sel, rule_body))
        i = end + 1
    return out


def prefix_selector_list(sel_str, prefix):
    """Split a selector list by commas (at top level only) and prefix each."""
    parts = []
    depth = 0
    buf = []
    for ch in sel_str:
        if ch in '([':
            depth += 1
            buf.append(ch)
        elif ch in ')]':
            depth -= 1
            buf.append(ch)
        elif ch == ',' and depth == 0:
            parts.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append(''.join(buf).strip())
    return ', '.join(f'{prefix} {p}' for p in parts if p)


def transform_block_body(body, prefix='html.dark'):
    rules = split_top_level_rules(body)
    out_lines = []
    for sel, rb in rules:
        new_sel = prefix_selector_list(sel, prefix)
        out_lines.append(f'{new_sel} {rb}')
    return '\n        '.join(out_lines)


def transform_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    out = []
    i = 0
    n = len(content)
    count = 0
    while i < n:
        idx = content.find(MEDIA_MARK, i)
        if idx == -1:
            out.append(content[i:])
            break
        out.append(content[i:idx])
        # find the opening {
        brace_start = content.find('{', idx)
        if brace_start == -1:
            out.append(content[idx:])
            break
        brace_end = find_matching_brace(content, brace_start)
        if brace_end == -1:
            out.append(content[idx:])
            break
        inner = content[brace_start + 1:brace_end]
        try:
            transformed = transform_block_body(inner)
        except ValueError:
            print(f"  ! Could not parse block at offset {idx}; leaving unchanged")
            out.append(content[idx:brace_end + 1])
            i = brace_end + 1
            continue
        out.append(transformed)
        count += 1
        i = brace_end + 1

    new_content = ''.join(out)

    # Sanity: each transformed media block removes exactly one `{ }` pair (the @media wrapper),
    # so final brace count should drop by exactly `count`.
    delta_open  = content.count('{') - new_content.count('{')
    delta_close = content.count('}') - new_content.count('}')
    if delta_open != count or delta_close != count:
        print(f"! Brace delta mismatch (expected {count}, got open={delta_open}, close={delta_close}) — aborting")
        return False

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Transformed {count} dark-mode media-query blocks in {os.path.basename(path)}")
    return True


if __name__ == '__main__':
    if not os.path.isfile(TEMPLATE):
        print(f"File not found: {TEMPLATE}")
        sys.exit(1)
    # Backup
    backup = TEMPLATE + '.bak_darkmode'
    if not os.path.isfile(backup):
        import shutil
        shutil.copy(TEMPLATE, backup)
        print(f"Backup -> {backup}")
    else:
        print(f"Backup already exists at {backup} (will not overwrite)")
    transform_file(TEMPLATE)

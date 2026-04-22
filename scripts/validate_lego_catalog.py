"""
Build-time validator for Banner Lego's BLOCK_CATALOG.

Parses templates/index.html, extracts each block's (table, alias) metadata,
then scans sqlFrom / sqlJoin / projections / sqlWhere strings for every
`<alias>.<column>` reference. Each column is verified against the real
schema loaded from data/field_info.txt + data/bansecr_columns.txt.

Exits with non-zero status if any invalid column is found, so this can
gate the build.

Usage:
    python scripts/validate_lego_catalog.py
"""

from __future__ import annotations
import os
import re
import sys

HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
TEMPLATE = os.path.join(ROOT, 'templates', 'index.html')
FIELD_INFO = os.path.join(ROOT, 'data', 'field_info.txt')
BANSECR_COLS = os.path.join(ROOT, 'data', 'bansecr_columns.txt')


def load_schema() -> dict[str, set[str]]:
    """Return {TABLE: {COL, COL, ...}} from all available column sources."""
    schema: dict[str, set[str]] = {}

    def add(table: str, col: str) -> None:
        t = table.strip().strip('"').strip().upper()
        c = col.strip().strip('"').strip().upper()
        if not t or not c:
            return
        #  Skip noise headers that slip through CSV escapes
        if not t[0].isalpha():
            return
        schema.setdefault(t, set()).add(c)

    if os.path.isfile(FIELD_INFO):
        with open(FIELD_INFO, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                parts = line.split('|', 2)
                if len(parts) < 2:
                    continue
                add(parts[0], parts[1])

    if os.path.isfile(BANSECR_COLS):
        with open(BANSECR_COLS, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip().strip('"')
                parts = line.split('|', 2)
                if len(parts) < 2:
                    continue
                add(parts[0], parts[1])

    return schema


def extract_catalog(html: str) -> str:
    """Slice out the BLOCK_CATALOG literal from templates/index.html."""
    m = re.search(r'var BLOCK_CATALOG = \{', html)
    if not m:
        raise RuntimeError("BLOCK_CATALOG not found")
    start = m.end() - 1  # at the '{'
    depth = 0
    i = start
    while i < len(html):
        ch = html[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return html[start:i + 1]
        i += 1
    raise RuntimeError("BLOCK_CATALOG not balanced")


BLOCK_RE = re.compile(r"'(\w+)'\s*:\s*\{", re.MULTILINE)


def slice_blocks(catalog: str):
    """Yield (key, body_str) for each block in the catalog."""
    for m in BLOCK_RE.finditer(catalog):
        key = m.group(1)
        start = m.end() - 1  # at '{'
        depth = 0
        i = start
        while i < len(catalog):
            ch = catalog[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    yield key, catalog[start:i + 1]
                    break
            i += 1


PROP_RE_TABLE = re.compile(r"\btable\s*:\s*'([A-Z][A-Z0-9_]+)'")
PROP_RE_ALIAS = re.compile(r"\balias\s*:\s*'([a-zA-Z_][a-zA-Z0-9_]*)'")
EXTRA_ALIAS_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*?)\s+([a-z][a-z0-9_]+)(?:\s+|$)")

#  Column reference: <alias>.<table>_<rest>   (column starts with same table prefix
#  as its real table name in Banner, e.g. si.spriden_id)
COL_REF_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-z][a-z0-9_]+)\b")

#  Extra aliases that appear in sqlJoin but aren't in the block's own `alias:` field
#  (e.g. sc2 self-join alias, g2 subquery alias). We map them by finding
#  `FROM <table> <alias>` and `JOIN <table> <alias>` patterns.
JOIN_ALIAS_RE = re.compile(
    r"(?:from|join)\s+(?:[a-z]+\.)?([a-z][a-z0-9_]*)\s+([a-z][a-z0-9_]*)",
    re.IGNORECASE,
)

#  Aliases we know are person/vendor references to SPRIDEN (second instance).
#  These can't be inferred from the block's `table:` since that refers to
#  something else. We detect them via the `FROM/JOIN spriden <alias>` pattern.


def build_alias_map(block_body: str, primary_table: str, primary_alias: str) -> dict[str, str]:
    """Return {alias -> TABLE} for every alias observed in this block's SQL."""
    amap: dict[str, str] = {}
    if primary_table and primary_alias:
        amap[primary_alias] = primary_table.upper()
    for m in JOIN_ALIAS_RE.finditer(block_body):
        table = m.group(1).upper()
        alias = m.group(2)
        # Ignore SQL keywords that may match (on, and, where, etc.)
        if alias.lower() in {
            'on', 'and', 'or', 'where', 'from', 'join', 'as', 'inner',
            'left', 'right', 'outer', 'select', 'is', 'null', 'not',
        }:
            continue
        amap[alias] = table
    return amap


def validate(schema: dict[str, set[str]]) -> int:
    if not os.path.isfile(TEMPLATE):
        print(f"template not found: {TEMPLATE}", file=sys.stderr)
        return 1
    with open(TEMPLATE, 'r', encoding='utf-8') as f:
        html = f.read()

    try:
        catalog = extract_catalog(html)
    except RuntimeError as e:
        print(f"! {e}", file=sys.stderr)
        return 1

    total_errors = 0
    total_blocks = 0
    missing_tables: set[str] = set()
    blocks_with_issues: list[str] = []

    for key, body in slice_blocks(catalog):
        total_blocks += 1
        tm = PROP_RE_TABLE.search(body)
        am = PROP_RE_ALIAS.search(body)
        primary_table = tm.group(1) if tm else ''
        primary_alias = am.group(1) if am else ''

        #  Filter blocks don't have a table; skip table validation on them
        if primary_table:
            if primary_table not in schema:
                #  Could be a synthetic table name or an unsupported module — record
                missing_tables.add(primary_table)

        amap = build_alias_map(body, primary_table, primary_alias)

        errors: list[tuple[str, str, str]] = []  # (alias, col, reason)
        seen: set[tuple[str, str]] = set()
        for m in COL_REF_RE.finditer(body):
            alias, col = m.group(1), m.group(2).upper()
            if (alias, col) in seen:
                continue
            seen.add((alias, col))
            #  Skip obvious non-column tokens
            if alias in {'Math', 'console', 'document', 'window', 'self'}:
                continue
            table = amap.get(alias)
            if not table:
                #  Unknown alias — could be a JS local var, not a SQL alias. Skip silently.
                continue
            if table not in schema:
                continue  # table unknown, nothing to check
            if col not in schema[table]:
                errors.append((alias, col, f'{alias}.{col.lower()} — {table}.{col} not found'))

        if errors:
            blocks_with_issues.append(key)
            total_errors += len(errors)
            print(f"\n  Block '{key}' (table={primary_table}):")
            for _, _, msg in errors:
                print(f"    [FAIL]{msg}")

    #  Summary
    print('\n' + '=' * 60)
    print(f"Lego validator: {total_blocks} blocks scanned")
    if missing_tables:
        print(f"  Tables not in local schema ({len(missing_tables)}): {', '.join(sorted(missing_tables))}")
        print(f"  (these are not errors — columns on them are unverifiable)")
    if total_errors:
        print(f"  [FAIL] {total_errors} invalid column reference(s) across {len(blocks_with_issues)} block(s)")
        return 2
    print('  [OK] All referenced columns exist in the schema')
    return 0


if __name__ == '__main__':
    schema = load_schema()
    print(f"Loaded schema: {len(schema)} tables, "
          f"{sum(len(v) for v in schema.values())} columns")
    sys.exit(validate(schema))

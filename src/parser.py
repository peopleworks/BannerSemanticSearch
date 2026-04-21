"""
Parser for Banner table_info.txt and field_info.txt files.
Handles pipe-delimited format with multi-line description edge cases.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ColumnInfo:
    name: str
    description: str


@dataclass
class TableInfo:
    name: str
    type: str  # "TABLE" or "VIEW"
    description: str
    columns: list = field(default_factory=list)
    module: str = ""


# Pattern for a valid table_info line: NAME|TYPE|DESC
TABLE_LINE_RE = re.compile(r'^([A-Za-z_$][A-Za-z0-9_$]*)\|(TABLE|VIEW)\|(.*)')


def parse_table_info(filepath: str) -> dict:
    """
    Parse table_info.txt (pipe-delimited: TABLE_NAME|TYPE|DESCRIPTION).
    Handles multi-line descriptions by detecting continuation lines.
    Returns dict[table_name -> TableInfo].
    """
    tables = {}
    current_table = None

    path = Path(filepath)
    text = path.read_text(encoding='utf-8', errors='replace')

    for line in text.splitlines():
        line = line.strip().strip('"')
        if not line:
            continue

        match = TABLE_LINE_RE.match(line)
        if match:
            name = match.group(1).upper()
            ttype = match.group(2)
            desc = match.group(3).strip()
            if desc == '(no comments)':
                desc = ''
            current_table = TableInfo(name=name, type=ttype, description=desc)
            tables[name] = current_table
        elif current_table:
            # Continuation of previous description
            current_table.description += ' ' + line

    return tables


#  Identifier sanity — skips SQL*Plus header garbage like TRIM(C.TABLE_NAME)
IDENT_RE = re.compile(r'^[A-Z_$][A-Z0-9_$]*$')


def parse_field_info(filepath: str, tables: dict, force_module: str = '') -> dict:
    """
    Parse field_info.txt (pipe-delimited: TABLE_NAME|COLUMN_NAME|DESCRIPTION).
    Attaches columns to existing TableInfo objects.
    Creates synthetic TableInfo for tables not in table_info.
    If force_module is set, any synthetic TableInfo gets that module stamped
    on it (used for BANSECR so the categorizer leaves it as 'Security').
    Returns the updated tables dict.
    """
    path = Path(filepath)
    text = path.read_text(encoding='utf-8', errors='replace')

    last_col = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Strip leading/trailing double quotes (Oracle SPOOL artifact)
        line = line.strip('"')
        if not line:
            continue

        parts = line.split('|', 2)
        if len(parts) < 2:
            # Continuation of previous column description
            if last_col:
                last_col.description += ' ' + line
            continue

        table_name = parts[0].strip().strip('"').upper()
        col_name = parts[1].strip().strip('"').upper()
        col_desc = parts[2].strip().strip('"') if len(parts) > 2 else ''

        if not table_name or not col_name:
            continue

        #  Reject SQL*Plus header garbage (parentheses, quotes, etc.)
        if not IDENT_RE.match(table_name) or not IDENT_RE.match(col_name):
            continue

        # Create synthetic table entry if not in table_info
        if table_name not in tables:
            tables[table_name] = TableInfo(
                name=table_name,
                type='TABLE',
                description='',
                module=force_module,
            )
        elif force_module and not tables[table_name].module:
            tables[table_name].module = force_module

        col = ColumnInfo(name=col_name, description=col_desc)
        tables[table_name].columns.append(col)
        last_col = col

    return tables


def parse_bansecr(data_dir: Path, tables: dict) -> dict:
    """
    Optionally parse the BANSECR security-schema extracts.
    These files are gitignored (local-only; not part of the public repo).
    Every BANSECR table is stamped with module='Security' so the prefix-based
    categorizer leaves it alone (BANSECR shares prefixes with General).
    """
    bs_tables_file = data_dir / 'bansecr_tables.txt'
    bs_cols_file   = data_dir / 'bansecr_columns.txt'

    if not bs_tables_file.exists() and not bs_cols_file.exists():
        return tables

    if bs_tables_file.exists():
        sec_tables = parse_table_info(str(bs_tables_file))
        for name, tinfo in sec_tables.items():
            tinfo.module = 'Security'
            tables[name] = tinfo

    if bs_cols_file.exists():
        tables = parse_field_info(str(bs_cols_file), tables, force_module='Security')

    return tables


def parse_all(data_dir: str) -> dict:
    """
    Parse both data files from the given directory.
    Returns dict[table_name -> TableInfo] with columns attached.
    """
    data_path = Path(data_dir)

    table_file = data_path / 'table_info.txt'
    field_file = data_path / 'field_info.txt'

    if not table_file.exists():
        raise FileNotFoundError(f"table_info.txt not found in {data_dir}")
    if not field_file.exists():
        raise FileNotFoundError(f"field_info.txt not found in {data_dir}")

    tables = parse_table_info(str(table_file))
    tables = parse_field_info(str(field_file), tables)

    # Optional: BANSECR security schema extracts (gitignored; local only)
    tables = parse_bansecr(data_path, tables)

    return tables

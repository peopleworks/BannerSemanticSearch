"""
SQL Explainer Prototype — Proof of Concept
==========================================
Parses a SQL query, looks up tables and columns in Banner schema data,
and generates a plain-English explanation.

This proves the concept for integrating into BannerSemanticSearch.
No AI required — just pattern matching + schema lookup.

Usage:
    python sql_explainer_prototype.py

Pedro's vision: paste SQL into BannerSemanticSearch, get
"This query is about... these columns mean... this join connects..."
"""

import re
from pathlib import Path


def load_schema(data_dir: str = "data"):
    """Load Banner schema from the same data files BannerSemanticSearch uses."""
    tables = {}
    columns = {}

    # Load table descriptions
    table_file = Path(data_dir) / "table_info.txt"
    if table_file.exists():
        for line in table_file.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split("|")
            if len(parts) >= 3:
                name = parts[0].strip().upper()
                tables[name] = {
                    "type": parts[1].strip(),
                    "desc": parts[2].strip(),
                }

    # Load column descriptions
    field_file = Path(data_dir) / "field_info.txt"
    if field_file.exists():
        for line in field_file.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split("|")
            if len(parts) >= 3:
                tbl = parts[0].strip().upper()
                col = parts[1].strip().upper()
                desc = parts[2].strip()
                if tbl not in columns:
                    columns[tbl] = {}
                columns[tbl][col] = desc

    # Load business cases
    cases = []
    cases_file = Path(data_dir) / "business_cases.txt"
    if cases_file.exists():
        for line in cases_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("CASE_ID"):
                continue  # skip header
            parts = line.split("|")
            if len(parts) >= 7:
                cases.append({
                    "id": parts[0].strip(),
                    "category": parts[1].strip(),
                    "title": parts[2].strip(),
                    "tables": [t.strip().upper() for t in parts[3].split(",")],
                    "description": parts[5].strip(),
                })

    return tables, columns, cases


def parse_sql(sql: str):
    """
    Extract tables, columns, joins, and conditions from a SQL query.
    Simple regex-based parser — handles 80% of real-world queries.
    """
    sql_upper = sql.upper()
    sql_clean = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)  # remove comments
    sql_clean = re.sub(r"/\*.*?\*/", "", sql_clean, flags=re.DOTALL)  # remove block comments
    sql_clean = " ".join(sql_clean.split())  # normalize whitespace

    result = {
        "tables": [],
        "aliases": {},
        "columns_selected": [],
        "joins": [],
        "conditions": [],
        "aggregations": [],
    }

    # Extract table references (FROM and JOIN)
    # Pattern: FROM/JOIN table_name [alias]
    table_pattern = r"(?:FROM|JOIN)\s+(\w+)\s+(\w+)?(?:\s+ON)?"
    for match in re.finditer(table_pattern, sql_clean, re.IGNORECASE):
        table = match.group(1).upper()
        alias = match.group(2).upper() if match.group(2) and match.group(2).upper() not in (
            "ON", "WHERE", "AND", "OR", "LEFT", "RIGHT", "INNER", "OUTER",
            "CROSS", "FULL", "JOIN", "GROUP", "ORDER", "HAVING", "SET",
        ) else None
        if table not in ("SELECT", "DUAL"):
            result["tables"].append(table)
            if alias:
                result["aliases"][alias] = table

    # Extract SELECT columns
    select_match = re.search(r"SELECT\s+(.*?)\s+FROM", sql_clean, re.IGNORECASE | re.DOTALL)
    if select_match:
        cols_str = select_match.group(1)
        for col_expr in cols_str.split(","):
            col_expr = col_expr.strip()
            if col_expr != "*":
                result["columns_selected"].append(col_expr)

    # Extract JOIN conditions
    on_pattern = r"ON\s+(.*?)(?=\s+(?:WHERE|JOIN|LEFT|RIGHT|INNER|GROUP|ORDER|$))"
    for match in re.finditer(on_pattern, sql_clean, re.IGNORECASE):
        result["joins"].append(match.group(1).strip())

    # Extract WHERE conditions
    where_match = re.search(r"WHERE\s+(.*?)(?=\s+(?:GROUP|ORDER|HAVING|$))", sql_clean, re.IGNORECASE)
    if where_match:
        conditions = re.split(r"\s+AND\s+", where_match.group(1), flags=re.IGNORECASE)
        result["conditions"] = [c.strip() for c in conditions]

    # Check for aggregations
    if re.search(r"\bSUM\b|\bCOUNT\b|\bAVG\b|\bMIN\b|\bMAX\b", sql_clean, re.IGNORECASE):
        result["aggregations"] = re.findall(
            r"(SUM|COUNT|AVG|MIN|MAX)\s*\([^)]+\)", sql_clean, re.IGNORECASE
        )

    # Resolve aliases in columns
    resolved_columns = []
    for col_expr in result["columns_selected"]:
        # Remove alias prefix (d.COLUMN -> COLUMN)
        col_clean = re.sub(r"\w+\.", "", col_expr).strip()
        # Remove AS alias
        col_clean = re.split(r"\s+AS\s+", col_clean, flags=re.IGNORECASE)[0].strip()
        # Remove function wrappers
        inner = re.search(r"\(([^)]+)\)", col_clean)
        if inner:
            col_clean = inner.group(1).strip()
            col_clean = re.sub(r"\w+\.", "", col_clean).strip()
        resolved_columns.append(col_clean.upper())
    result["resolved_columns"] = resolved_columns

    return result


def find_matching_cases(tables: list, cases: list):
    """Find business cases that reference the same tables."""
    table_set = set(t.upper() for t in tables)
    matches = []
    for case in cases:
        case_tables = set(case["tables"])
        overlap = table_set & case_tables
        if len(overlap) >= 2 or (len(overlap) == 1 and len(case_tables) == 1):
            score = len(overlap) / max(len(case_tables), 1)
            matches.append((score, case))
    matches.sort(key=lambda x: -x[0])
    return matches[:5]


def explain_sql(sql: str, tables: dict, columns: dict, cases: list):
    """Generate a plain-English explanation of a SQL query."""
    parsed = parse_sql(sql)

    lines = []
    lines.append("=" * 70)
    lines.append("  SQL EXPLAINER — Banner Query Analysis")
    lines.append("=" * 70)
    lines.append("")

    # --- Tables ---
    lines.append("TABLES USED:")
    for tbl in parsed["tables"]:
        info = tables.get(tbl)
        alias_str = ""
        for a, t in parsed["aliases"].items():
            if t == tbl:
                alias_str = f" (alias: {a})"
        if info:
            lines.append(f"  {tbl}{alias_str}")
            lines.append(f"    Type: {info['type']}")
            lines.append(f"    Purpose: {info['desc']}")
        else:
            lines.append(f"  {tbl}{alias_str} — (not found in schema)")
        lines.append("")

    # --- Columns Selected ---
    if parsed["resolved_columns"]:
        lines.append("COLUMNS SELECTED:")
        for col in parsed["resolved_columns"]:
            if col == "*":
                lines.append("  * (all columns)")
                continue
            # Find which table owns this column
            found = False
            for tbl in parsed["tables"]:
                tbl_cols = columns.get(tbl, {})
                if col in tbl_cols:
                    lines.append(f"  {tbl}.{col}")
                    lines.append(f"    Meaning: {tbl_cols[col]}")
                    found = True
                    break
            if not found:
                lines.append(f"  {col} — (description not found)")
        lines.append("")

    # --- Joins ---
    if parsed["joins"]:
        lines.append("HOW TABLES CONNECT:")
        for join in parsed["joins"]:
            lines.append(f"  {join}")
            # Try to explain the join column
            join_cols = re.findall(r"(\w+)\.(\w+)", join)
            for alias, col in join_cols:
                real_table = parsed["aliases"].get(alias.upper(), alias.upper())
                tbl_cols = columns.get(real_table, {})
                col_upper = col.upper()
                if col_upper in tbl_cols:
                    lines.append(f"    {real_table}.{col_upper}: {tbl_cols[col_upper]}")
            # Explain common join patterns
            if "PIDM" in join.upper():
                lines.append("    >>Joining by Person ID (unique employee/student identifier)")
            if "PAYNO" in join.upper():
                lines.append("    >>Joining by Pay Number (specific payroll within the year)")
            if "PICT_CODE" in join.upper():
                lines.append("    >>Joining by Payroll ID Code (SP=Staff, SF=Faculty)")
            if "SEQ_NO" in join.upper():
                lines.append("    >>Joining by Sequence Number (original vs adjustment records)")
            if "YEAR" in join.upper():
                lines.append("    >>Joining by Payroll Year")
            if "TERM_CODE" in join.upper():
                lines.append("    >>Joining by Academic Term")
        lines.append("")

    # --- Conditions ---
    if parsed["conditions"]:
        lines.append("FILTERS APPLIED:")
        for cond in parsed["conditions"]:
            lines.append(f"  {cond}")
            # Explain known patterns
            cond_upper = cond.upper()
            if "DISP" in cond_upper and ">=" in cond_upper and "60" in cond_upper:
                lines.append("    >>Only POSTED transactions (completed payroll runs)")
            if "PICT_CODE" in cond_upper and "SP" in cond_upper:
                lines.append("    >>Staff/Professional payroll only")
            if "PICT_CODE" in cond_upper and "SF" in cond_upper:
                lines.append("    >>Faculty payroll only")
            if "BDCA_CODE" in cond_upper:
                code_match = re.search(r"'(\w+)'", cond)
                if code_match:
                    code = code_match.group(1).upper()
                    code_map = {
                        "FED": "Federal Income Tax",
                        "FIM": "FICA Medicare (Employee + Employer)",
                        "FIO": "FICA Social Security (Employee + Employer)",
                        "FIA": "Additional Medicare (>$200K wages)",
                        "ILL": "Illinois State Income Tax",
                        "MCH": "Michigan State Income Tax",
                        "NYT": "New York State Income Tax",
                        "S1R": "SURS Tier 1 Retirement",
                        "S2G": "SURS Tier 2 (eff 2011)",
                        "S2R": "SURS Tier 2 New (eff 2014)",
                    }
                    if code in code_map:
                        lines.append(f"    >>Deduction code '{code}' = {code_map[code]}")
            if "CHANGE_IND" in cond_upper and "NULL" in cond_upper:
                lines.append("    >>Current name record only (excludes name change history)")
            if "PTRCALN_END_DATE" in cond_upper and "BETWEEN" in cond_upper:
                months = re.findall(r"\d+", cond)
                if len(months) >= 2:
                    quarter_map = {
                        ("1", "3"): "Q1 (January–March)",
                        ("4", "6"): "Q2 (April–June)",
                        ("7", "9"): "Q3 (July–September)",
                        ("10", "12"): "Q4 (October–December)",
                    }
                    q = quarter_map.get((months[-2], months[-1]), f"months {months[-2]}-{months[-1]}")
                    lines.append(f"    >>Filtering to {q}")
        lines.append("")

    # --- Aggregations ---
    if parsed["aggregations"]:
        lines.append("CALCULATIONS:")
        for agg in parsed["aggregations"]:
            lines.append(f"  {agg}")
            if "SUM" in agg.upper():
                lines.append("    >>Totaling amounts across all matching records")
            if "COUNT" in agg.upper():
                lines.append("    >>Counting records or distinct values")
        lines.append("")

    # --- Business Cases ---
    matching_cases = find_matching_cases(parsed["tables"], cases)
    if matching_cases:
        lines.append("RELATED BUSINESS CASES:")
        for score, case in matching_cases[:3]:
            lines.append(f"  [{case['id']}] {case['title']}")
            lines.append(f"    {case['description'][:150]}...")
        lines.append("")

    # --- Summary ---
    lines.append("SUMMARY:")
    summary_parts = []
    if any("PHRDEDN" in t for t in parsed["tables"]):
        summary_parts.append("payroll deduction data")
    if any("PHRHIST" in t for t in parsed["tables"]):
        summary_parts.append("payroll history")
    if any("SPRIDEN" in t for t in parsed["tables"]):
        summary_parts.append("employee identity")
    if any("SPBPERS" in t for t in parsed["tables"]):
        summary_parts.append("personal demographics")
    if any("PEBEMPL" in t for t in parsed["tables"]):
        summary_parts.append("employment records")
    if any("PTRCALN" in t for t in parsed["tables"]):
        summary_parts.append("pay calendar dates")
    if any("SPRADDR" in t for t in parsed["tables"]):
        summary_parts.append("address information")

    if summary_parts:
        lines.append(f"  This query retrieves {', '.join(summary_parts)}.")
    else:
        lines.append(f"  This query uses: {', '.join(parsed['tables'])}")

    # Add context from conditions
    for cond in parsed["conditions"]:
        if "BDCA_CODE" in cond.upper():
            code_match = re.search(r"'(\w+)'", cond)
            if code_match:
                lines.append(f"  Focused on deduction code: {code_match.group(1)}")
        if "YEAR" in cond.upper():
            year_match = re.search(r"(\d{4})", cond)
            if year_match:
                lines.append(f"  For payroll year: {year_match.group(1)}")

    if parsed["aggregations"]:
        lines.append("  Results are AGGREGATED (totals/counts, not individual records).")
    else:
        lines.append("  Results are DETAIL-LEVEL (one row per matching record).")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


# ============================================================================
# DEMO
# ============================================================================
if __name__ == "__main__":
    print("Loading Banner schema...")
    tables, columns, cases = load_schema()
    print(f"  Loaded {len(tables)} tables, {sum(len(v) for v in columns.values())} columns, {len(cases)} business cases")
    print()

    # Test with a real query from our ADP project
    test_sql = """
        SELECT
            d.PHRDEDN_BDCA_CODE AS code,
            ROUND(SUM(d.PHRDEDN_EMPLOYEE_AMT), 2) AS ee_withheld,
            ROUND(SUM(d.PHRDEDN_EMPLOYER_AMT), 2) AS er_withheld,
            ROUND(SUM(d.PHRDEDN_APPLICABLE_GROSS), 2) AS applicable_gross,
            COUNT(DISTINCT d.PHRDEDN_PIDM) AS employee_count
        FROM PHRDEDN d
        JOIN PHRHIST h
            ON  h.PHRHIST_PIDM      = d.PHRDEDN_PIDM
            AND h.PHRHIST_YEAR      = d.PHRDEDN_YEAR
            AND h.PHRHIST_PAYNO     = d.PHRDEDN_PAYNO
            AND h.PHRHIST_PICT_CODE = d.PHRDEDN_PICT_CODE
            AND h.PHRHIST_SEQ_NO    = d.PHRDEDN_SEQ_NO
        WHERE d.PHRDEDN_YEAR      = 2025
          AND h.PHRHIST_PICT_CODE IN ('SP', 'SF')
          AND h.PHRHIST_DISP      >= '60'
          AND d.PHRDEDN_BDCA_CODE IN ('FED', 'FIO', 'FIM', 'FIA')
          AND EXISTS (
              SELECT 1 FROM PTRCALN c
              WHERE c.PTRCALN_YEAR      = h.PHRHIST_YEAR
                AND c.PTRCALN_PICT_CODE = h.PHRHIST_PICT_CODE
                AND c.PTRCALN_PAYNO     = h.PHRHIST_PAYNO
                AND EXTRACT(MONTH FROM c.PTRCALN_END_DATE) BETWEEN 10 AND 12
          )
        GROUP BY d.PHRDEDN_BDCA_CODE
        ORDER BY d.PHRDEDN_BDCA_CODE
    """

    print(explain_sql(test_sql, tables, columns, cases))

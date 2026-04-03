"""
Banner table relationship engine.
Infers relationships from column naming patterns AND reads formal FKs if available.

Banner follows strict naming conventions:
  - TABLE_PIDM          -> links to SPRIDEN (person)
  - TABLE_TERM_CODE     -> links to STVTERM (term)
  - TABLE_CAMP_CODE     -> links to STVCAMP (campus)
  - TABLE_ECLS_CODE     -> links to PTRECLS (employee class)
  - TABLE_POSN          -> links to NBBPOSN (position)
  - TABLE_FUND_CODE     -> links to FTVFUND (fund)
  etc.

This is NOT AI -- it's domain knowledge encoded as rules.
"""

from collections import defaultdict
from pathlib import Path


# ============================================================
# Banner column-suffix -> target table mapping
# These are well-known Banner conventions
# ============================================================
COLUMN_SUFFIX_RULES = {
    # Person / Identity
    '_PIDM':            ('SPRIDEN', 'Person (PIDM)', 'Links to person/entity identification'),
    # Academic / Student
    '_TERM_CODE':       ('STVTERM', 'Term', 'Academic term validation'),
    '_TERM_CODE_EFF':   ('STVTERM', 'Term (Effective)', 'Effective academic term'),
    '_PTRM_CODE':       ('STVPTRM', 'Part of Term', 'Part of term validation'),
    '_CAMP_CODE':       ('STVCAMP', 'Campus', 'Campus validation'),
    '_COLL_CODE':       ('STVCOLL', 'College', 'College validation'),
    '_DEPT_CODE':       ('STVDEPT', 'Department', 'Academic department validation'),
    '_LEVL_CODE':       ('STVLEVL', 'Level', 'Student level validation (UG/GR)'),
    '_DEGC_CODE':       ('STVDEGC', 'Degree', 'Degree code validation'),
    '_MAJR_CODE':       ('STVMAJR', 'Major', 'Major/program validation'),
    '_MAJR_CODE_CONC':  ('STVMAJR', 'Concentration', 'Concentration code validation'),
    '_SUBJ_CODE':       ('STVSUBJ', 'Subject', 'Subject area validation'),
    '_CRSE_NUMB':       ('SCBCRSE', 'Course', 'Course catalog reference'),
    '_ATTS_CODE':       ('STVATTS', 'Attribute', 'Course attribute validation'),
    '_STYP_CODE':       ('STVSTYP', 'Student Type', 'Student type validation'),
    '_RESD_CODE':       ('STVRESD', 'Residency', 'Residency status validation'),
    '_ADMT_CODE':       ('STVADMT', 'Admit Type', 'Admission type validation'),
    '_SITE_CODE':       ('STVSITE', 'Site', 'Off-campus site validation'),
    '_STSP_CODE':       ('STVSTSP', 'Student Status', 'Student status validation'),
    '_SESS_CODE':       ('STVSESS', 'Session', 'Session validation'),
    '_SCHD_CODE':       ('STVSCHD', 'Schedule Type', 'Schedule type validation'),
    '_INSM_CODE':       ('STVINSM', 'Instructional Method', 'Instruction method validation'),
    '_GRDE_CODE':       ('SHRGRDE', 'Grade', 'Grade code validation'),
    # Person demographics
    '_ATYP_CODE':       ('STVATYP', 'Address Type', 'Address type validation'),
    '_TELE_CODE':       ('STVTELE', 'Telephone Type', 'Phone type validation'),
    '_EMAL_CODE':       ('STVEMAL', 'Email Type', 'Email type validation'),
    '_NATN_CODE':       ('STVNATN', 'Nation', 'Nation/country validation'),
    '_STAT_CODE':       ('STVSTAT', 'State/Province', 'State/province validation'),
    '_CNTY_CODE':       ('STVCNTY', 'County', 'County validation'),
    '_ETHN_CODE':       ('STVETHN', 'Ethnicity', 'Ethnicity validation'),
    '_MRTL_CODE':       ('STVMRTL', 'Marital Status', 'Marital status validation'),
    '_RELT_CODE':       ('STVRELT', 'Relationship', 'Relationship type validation'),
    '_CITZ_CODE':       ('STVCITZ', 'Citizenship', 'Citizenship status validation'),
    '_VISA_CODE':       ('STVVISA', 'Visa Type', 'Visa type validation'),
    '_LGCY_CODE':       ('STVLGCY', 'Legacy', 'Legacy status validation'),
    # HR / Payroll
    '_ECLS_CODE':       ('PTRECLS', 'Employee Class', 'Employee classification validation'),
    '_BCAT_CODE':       ('PTRBCAT', 'Benefit Category', 'Benefit category validation'),
    '_BDCA_CODE':       ('PTRBDCA', 'Benefit/Deduction', 'Benefit/deduction code validation'),
    '_EARN_CODE':       ('PTREARN', 'Earnings Code', 'Earnings type validation'),
    '_PICT_CODE':       ('PTRPICT', 'Payroll ID', 'Payroll calendar ID validation'),
    '_POSN':            ('NBBPOSN', 'Position', 'Position definition reference'),
    '_JBLN_CODE':       ('PTRJBLN', 'Job Location', 'Job location validation'),
    '_EMPS_CODE':       ('STVEMPS', 'Employer Status', 'Employer status validation'),
    '_WKSH_CODE':       ('PTRWKSH', 'Work Schedule', 'Work schedule validation'),
    '_LEAV_CODE':       ('PTRLEAV', 'Leave Type', 'Leave type validation'),
    '_LCAT_CODE':       ('PTRLCAT', 'Leave Category', 'Leave category validation'),
    '_DICD_CODE':       ('PTRDICD', 'Distribution', 'Distribution code validation'),
    # Finance
    '_FUND_CODE':       ('FTVFUND', 'Fund', 'Finance fund validation'),
    '_ORGN_CODE':       ('FTVORGN', 'Organization', 'Finance organization validation'),
    '_ACCT_CODE':       ('FTVACCT', 'Account', 'Finance account validation'),
    '_PROG_CODE':       ('FTVPROG', 'Program', 'Finance program validation'),
    '_ACTV_CODE':       ('FTVACTV', 'Activity', 'Finance activity validation'),
    '_LOCN_CODE':       ('FTVLOCN', 'Location', 'Finance location validation'),
    '_BANK_CODE':       ('GXVBANK', 'Bank', 'Bank routing validation'),
    '_COAS_CODE':       ('FTVCOAS', 'Chart of Accounts', 'Chart of accounts validation'),
    '_ATYP_CODE':       ('STVATYP', 'Address Type', 'Address type validation'),
    # Financial Aid
    '_TREQ_CODE':       ('RTVTREQ', 'Tracking Req', 'FA tracking requirement validation'),
    '_FUND_CODE':       ('FTVFUND', 'Fund', 'Finance fund validation'),
    '_APRD_CODE':       ('RTVAPRD', 'Aid Period', 'Aid period validation'),
    '_AWST_CODE':       ('RTVAWST', 'Award Status', 'Award status validation'),
    # General / System
    '_VPDI_CODE':       ('GTVVPDI', 'VPDI', 'Virtual PDI institution validation'),
    '_PTYP_CODE':       ('GTVPTYP', 'Process Type', 'Process type validation'),
    '_DISP_CODE':       ('GTVDISP', 'Disposition', 'Disposition validation'),
    '_SBGI_CODE':       ('STVSBGI', 'Source/BG Inst', 'Source/background institution'),
}


def infer_relationships(tables: dict) -> dict:
    """
    Infer table relationships from Banner column naming conventions.

    Returns dict:
    {
        'TABLE_NAME': {
            'references': [  # This table points TO other tables
                {'column': 'COL_NAME', 'target_table': 'TARGET', 'label': 'Label', 'desc': 'Description'},
            ],
            'referenced_by': [  # Other tables point TO this table
                {'source_table': 'SOURCE', 'source_column': 'COL_NAME', 'label': 'Label'},
            ],
        }
    }
    """
    relationships = defaultdict(lambda: {'references': [], 'referenced_by': []})

    for table_name, table in tables.items():
        for col in table.columns:
            col_name = col.name.upper()

            # Try to match the column suffix against known patterns
            # Strip the table prefix first: PEBEMPL_ECLS_CODE -> _ECLS_CODE
            parts = col_name.split('_', 1)
            if len(parts) < 2:
                continue

            suffix = '_' + parts[1]

            # Try longest suffix match first
            matched = None
            for rule_suffix in sorted(COLUMN_SUFFIX_RULES.keys(), key=len, reverse=True):
                if suffix.endswith(rule_suffix):
                    matched = rule_suffix
                    break

            if not matched:
                continue

            target_table, label, desc = COLUMN_SUFFIX_RULES[matched]

            # Don't create self-references
            if target_table == table_name:
                continue

            # Only create reference if target table exists in our data
            if target_table in tables:
                relationships[table_name]['references'].append({
                    'column': col_name,
                    'target_table': target_table,
                    'label': label,
                    'desc': desc,
                })
                relationships[target_table]['referenced_by'].append({
                    'source_table': table_name,
                    'source_column': col_name,
                    'label': label,
                })

    # Deduplicate and sort
    for table_name in relationships:
        refs = relationships[table_name]['references']
        # Deduplicate by (column, target)
        seen = set()
        unique_refs = []
        for r in refs:
            key = (r['column'], r['target_table'])
            if key not in seen:
                seen.add(key)
                unique_refs.append(r)
        relationships[table_name]['references'] = sorted(unique_refs, key=lambda x: x['label'])

        refby = relationships[table_name]['referenced_by']
        # Deduplicate by source_table (keep count)
        source_counts = defaultdict(int)
        source_labels = {}
        for r in refby:
            source_counts[r['source_table']] += 1
            source_labels[r['source_table']] = r['label']
        relationships[table_name]['referenced_by'] = sorted([
            {'source_table': st, 'count': c, 'label': source_labels[st]}
            for st, c in source_counts.items()
        ], key=lambda x: -x['count'])

    return dict(relationships)


def parse_formal_relationships(filepath: str) -> list:
    """
    Parse formal FK relationships from extract_relationships.sql output.
    Format: CHILD_TABLE|CHILD_COLUMN|PARENT_TABLE|PARENT_COLUMN|CONSTRAINT_NAME
    Returns list of relationship dicts.
    """
    path = Path(filepath)
    if not path.exists():
        return []

    formal = []
    text = path.read_text(encoding='utf-8', errors='replace')
    for line in text.splitlines():
        line = line.strip().strip('"')
        if not line:
            continue
        # Skip header line (contains SQL column aliases)
        if 'TABLE_NAME' in line.upper() and 'COLUMN_NAME' in line.upper():
            continue
        parts = line.split('|')
        if len(parts) >= 4:
            formal.append({
                'child_table': parts[0].strip().strip('"').upper(),
                'child_column': parts[1].strip().strip('"').upper(),
                'parent_table': parts[2].strip().strip('"').upper(),
                'parent_column': parts[3].strip().strip('"').upper(),
                'constraint': parts[4].strip().strip('"') if len(parts) > 4 else '',
            })
    return formal


def merge_formal_relationships(inferred: dict, formal: list, tables: dict) -> dict:
    """
    Merge formal FK relationships into the inferred relationship map.
    Formal FKs get a 'formal' flag so the UI can distinguish them.
    """
    for fk in formal:
        child = fk['child_table']
        parent = fk['parent_table']

        if child not in tables or parent not in tables:
            continue

        if child not in inferred:
            inferred[child] = {'references': [], 'referenced_by': []}
        if parent not in inferred:
            inferred[parent] = {'references': [], 'referenced_by': []}

        # Check if this reference already exists (from inference)
        exists = any(
            r['column'] == fk['child_column'] and r['target_table'] == parent
            for r in inferred[child]['references']
        )

        if not exists:
            inferred[child]['references'].append({
                'column': fk['child_column'],
                'target_table': parent,
                'target_column': fk['parent_column'],
                'label': 'FK',
                'desc': f"FK {fk['constraint']}: {fk['child_column']} \u2192 {parent}.{fk['parent_column']}",
                'formal': True,
            })

    return inferred


def build_relationships(tables: dict, data_dir: str) -> dict:
    """
    Build complete relationship map: inferred + formal (if available).
    """
    # Step 1: Infer from column naming patterns
    rels = infer_relationships(tables)

    # Step 2: Merge formal FKs if file exists
    formal_file = Path(data_dir) / 'relationships.txt'
    if formal_file.exists():
        formal = parse_formal_relationships(str(formal_file))
        rels = merge_formal_relationships(rels, formal, tables)
        print(f'       Merged {len(formal)} formal FK constraints')

    # Count stats
    total_refs = sum(len(r['references']) for r in rels.values())
    tables_with_refs = sum(1 for r in rels.values() if r['references'] or r['referenced_by'])

    print(f'       {total_refs:,} relationships inferred across {tables_with_refs:,} tables')

    return rels


def serialize_relationships(rels: dict) -> dict:
    """
    Serialize relationships to compact JSON for embedding in HTML.
    """
    compact = {}
    for table_name, data in rels.items():
        if not data['references'] and not data['referenced_by']:
            continue

        entry = {}
        if data['references']:
            # [{col, target, label, desc, formal?}]
            entry['refs'] = [
                [r['column'], r['target_table'], r['label'], r.get('desc', ''), r.get('formal', False)]
                for r in data['references'][:50]  # Limit per table
            ]
        if data['referenced_by']:
            # [{source, count, label}]
            entry['refBy'] = [
                [r['source_table'], r['count'], r['label']]
                for r in data['referenced_by'][:100]  # Limit
            ]

        compact[table_name] = entry

    return compact

"""
Categorize Banner tables into functional modules based on naming conventions.
"""

# Banner module definitions: prefix -> (module_name, description)
# Ordered by prefix length (longest first for matching priority)
MODULE_MAP = {
    # Advancement / Alumni
    'AF':  ('Advancement', 'Advancement/Alumni/Development'),
    'AG':  ('Advancement', 'Advancement/Alumni/Development'),
    'AM':  ('Advancement', 'Advancement/Alumni/Development'),
    'AN':  ('Advancement', 'Advancement/Alumni/Development'),
    'AP':  ('Advancement', 'Advancement/Alumni/Development'),
    'AR':  ('Advancement', 'Advancement/Alumni/Development'),
    'AS':  ('Advancement', 'Advancement/Alumni/Development'),
    'AT':  ('Advancement', 'Advancement/Alumni/Development'),
    'AU':  ('Advancement', 'Advancement/Alumni/Development'),
    'AX':  ('Advancement', 'Advancement/Alumni/Development'),
    # Finance
    'FA':  ('Finance', 'Finance/Budgeting/Purchasing'),
    'FB':  ('Finance', 'Finance/Budgeting/Purchasing'),
    'FC':  ('Finance', 'Finance/Budgeting/Purchasing'),
    'FG':  ('Finance', 'Finance/Budgeting/Purchasing'),
    'FI':  ('Finance', 'Finance/Budgeting/Purchasing'),
    'FN':  ('Finance', 'Finance/Budgeting/Purchasing'),
    'FO':  ('Finance', 'Finance/Budgeting/Purchasing'),
    'FP':  ('Finance', 'Finance/Budgeting/Purchasing'),
    'FR':  ('Finance', 'Finance/Budgeting/Purchasing'),
    'FT':  ('Finance', 'Finance/Budgeting/Purchasing'),
    'FV':  ('Finance', 'Finance/Budgeting/Purchasing'),
    # General
    'GA':  ('General', 'General/Cross-Module'),
    'GB':  ('General', 'General/Cross-Module'),
    'GC':  ('General', 'General/Cross-Module'),
    'GE':  ('General', 'General/Cross-Module'),
    'GL':  ('General', 'General/Cross-Module'),
    'GO':  ('General', 'General/Cross-Module'),
    'GR':  ('General', 'General/Cross-Module'),
    'GT':  ('General', 'General/Cross-Module'),
    'GU':  ('General', 'General/Cross-Module'),
    'GV':  ('General', 'General/Cross-Module'),
    'GX':  ('General', 'General/Cross-Module'),
    'GJ':  ('General', 'General/Cross-Module'),
    # Position Control / Budget
    'NB':  ('Position Control', 'Position Budgeting/Control'),
    'NR':  ('Position Control', 'Position Budgeting/Control'),
    'NV':  ('Position Control', 'Position Budgeting/Control'),
    # Human Resources / Payroll
    'PA':  ('Human Resources', 'HR/Payroll/Benefits'),
    'PB':  ('Human Resources', 'HR/Payroll/Benefits'),
    'PD':  ('Human Resources', 'HR/Payroll/Benefits'),
    'PE':  ('Human Resources', 'HR/Payroll/Benefits'),
    'PH':  ('Human Resources', 'HR/Payroll/Benefits'),
    'PJ':  ('Human Resources', 'HR/Payroll/Benefits'),
    'PP':  ('Human Resources', 'HR/Payroll/Benefits'),
    'PR':  ('Human Resources', 'HR/Payroll/Benefits'),
    'PT':  ('Human Resources', 'HR/Payroll/Benefits'),
    'PW':  ('Human Resources', 'HR/Payroll/Benefits'),
    'PX':  ('Human Resources', 'HR/Payroll/Benefits'),
    'PV':  ('Human Resources', 'HR/Payroll/Benefits'),
    # Financial Aid
    'RB':  ('Financial Aid', 'Student Financial Aid'),
    'RC':  ('Financial Aid', 'Student Financial Aid'),
    'RF':  ('Financial Aid', 'Student Financial Aid'),
    'RL':  ('Financial Aid', 'Student Financial Aid'),
    'RM':  ('Financial Aid', 'Student Financial Aid'),
    'RN':  ('Financial Aid', 'Student Financial Aid'),
    'RP':  ('Financial Aid', 'Student Financial Aid'),
    'RR':  ('Financial Aid', 'Student Financial Aid'),
    'RT':  ('Financial Aid', 'Student Financial Aid'),
    'RV':  ('Financial Aid', 'Student Financial Aid'),
    # Student
    'SA':  ('Student', 'Admissions/Registration/Records'),
    'SB':  ('Student', 'Admissions/Registration/Records'),
    'SC':  ('Student', 'Admissions/Registration/Records'),
    'SF':  ('Student', 'Admissions/Registration/Records'),
    'SG':  ('Student', 'Admissions/Registration/Records'),
    'SH':  ('Student', 'Admissions/Registration/Records'),
    'SK':  ('Student', 'Admissions/Registration/Records'),
    'SL':  ('Student', 'Admissions/Registration/Records'),
    'SM':  ('Student', 'Admissions/Registration/Records'),
    'SO':  ('Student', 'Admissions/Registration/Records'),
    'SP':  ('Student', 'Admissions/Registration/Records'),
    'SR':  ('Student', 'Admissions/Registration/Records'),
    'SS':  ('Student', 'Admissions/Registration/Records'),
    'ST':  ('Student', 'Admissions/Registration/Records'),
    'SV':  ('Student', 'Admissions/Registration/Records'),
    # Student Accounts / AR
    'TB':  ('Accounts Receivable', 'Student Accounts/Cashiering'),
    'TF':  ('Accounts Receivable', 'Student Accounts/Cashiering'),
    'TS':  ('Accounts Receivable', 'Student Accounts/Cashiering'),
    'TV':  ('Accounts Receivable', 'Student Accounts/Cashiering'),
    'TT':  ('Accounts Receivable', 'Student Accounts/Cashiering'),
    'TP':  ('Accounts Receivable', 'Student Accounts/Cashiering'),
    # Communication Management
    'GU':  ('Communication', 'Communication Management'),
    # Catalog / Schedule
    'SC':  ('Student', 'Admissions/Registration/Records'),
}

# Special longer prefixes (checked first)
LONG_PREFIX_MAP = {
    'GCRQRTZ': ('System', 'Scheduled Jobs/System'),
    'GCRSARL': ('System', 'Scheduled Jobs/System'),
    'WCC':    ('Custom', 'Institution Custom Tables'),
    'DW_':    ('Data Warehouse', 'Reporting/Data Warehouse'),
}


def get_module(table_name: str) -> tuple:
    """
    Determine the Banner module for a table based on its name prefix.
    Returns (module_name, module_description).
    """
    upper = table_name.upper()

    # Check long prefixes first
    for prefix, mod_info in LONG_PREFIX_MAP.items():
        if upper.startswith(prefix):
            return mod_info

    # For views like AF_ACCOUNT_DETAIL_VIEW, use the part before first underscore
    if '_' in upper:
        prefix_part = upper.split('_')[0]
        # Try the full prefix part first (e.g., "AF")
        if prefix_part in MODULE_MAP:
            return MODULE_MAP[prefix_part]

    # Try first 2 characters
    prefix2 = upper[:2]
    if prefix2 in MODULE_MAP:
        return MODULE_MAP[prefix2]

    return ('Other', 'Uncategorized')


def categorize_tables(tables: dict) -> dict:
    """
    Assign module to each TableInfo in the dict.
    Returns a module summary: {module_name: {description, count, prefixes}}.
    """
    module_summary = {}

    for table in tables.values():
        mod_name, mod_desc = get_module(table.name)
        table.module = mod_name

        if mod_name not in module_summary:
            module_summary[mod_name] = {
                'description': mod_desc,
                'count': 0,
                'tables_count': 0,
                'views_count': 0,
            }

        module_summary[mod_name]['count'] += 1
        if table.type == 'TABLE':
            module_summary[mod_name]['tables_count'] += 1
        else:
            module_summary[mod_name]['views_count'] += 1

    return module_summary

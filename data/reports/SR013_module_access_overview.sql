-- REPORT_ID: SR013
-- TITLE: Banner Module Access Overview — discover every module on your site
-- CATEGORY: Inventory
-- TABLES: GURAOBJ, GTVSYSI, GUVUACC
-- SEVERITY: INFO
-- DESCRIPTION: One row per distinct GURAOBJ_SYSI_CODE with the module's human name (from GTVSYSI), the number of Banner forms that belong to it, the number of distinct users with effective access somewhere in the module, and the write-capable grant count. Use this as the menu of modules you can hand to SR012 for a per-user-per-form breakdown. Finance is just one cell in this table — the rest of the business will want their own.
-- WHEN_TO_USE: First run for any new Banner security engagement — before picking a module to audit, see what modules actually exist on your site and how large they are. Also answer the question 'which modules are most widely accessed?' — a module with 300 users behind it deserves more attention than one with 12. Pair with SR012 (per-user forms in one module) for the deep-dive.
-- CAVEATS: GTVSYSI lives in the GENERAL schema (not BANSECR). Objects with a NULL GURAOBJ_SYSI_CODE are counted as '(unassigned)' — typically custom forms, non-Banner objects, or data from GURUOBJ rows whose object was never registered in GURAOBJ. Some sites use non-standard sysi codes (e.g. 'L' for Location Management) — the report lists whatever codes you actually have, not a hard-coded catalog. Canonical Ellucian codes: F=Finance, S=Student, P=HR/Payroll, A=Advancement, R=Financial Aid, T=Accounts Receivable, G=General, N=Position Control.

SELECT
    NVL(ao.guraobj_sysi_code, '(unassigned)')             AS module_code,
    sy.gtvsysi_desc                                       AS module_name,
    COUNT(DISTINCT ao.guraobj_object)                     AS form_count,
    COUNT(DISTINCT gu.guvuacc_user)                       AS distinct_users,
    COUNT(gu.guvuacc_user)                                AS total_grants,
    COUNT(CASE WHEN gu.guvuacc_role LIKE '%\_M' ESCAPE '\' THEN 1 END) AS maintenance_grants,
    COUNT(CASE WHEN gu.guvuacc_role LIKE '%\_Q' ESCAPE '\' THEN 1 END) AS query_grants,
    COUNT(CASE WHEN gu.guvuacc_type = 'Class'  THEN 1 END) AS via_class_grants,
    COUNT(CASE WHEN gu.guvuacc_type = 'Direct' THEN 1 END) AS via_direct_grants,
    COUNT(CASE WHEN gu.guvuacc_type LIKE 'Group%' THEN 1 END) AS via_group_grants
FROM        bansecr.guraobj ao
LEFT JOIN   general.gtvsysi sy ON sy.gtvsysi_code = ao.guraobj_sysi_code
LEFT JOIN   bansecr.guvuacc gu ON gu.guvuacc_object = ao.guraobj_object
GROUP BY    ao.guraobj_sysi_code, sy.gtvsysi_desc
ORDER BY    distinct_users DESC NULLS LAST, form_count DESC;

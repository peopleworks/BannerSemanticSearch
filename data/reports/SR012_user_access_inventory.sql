-- REPORT_ID: SR012
-- TITLE: Banner User Access Inventory — Finance Module
-- CATEGORY: Inventory
-- TABLES: GUVUACC, GURAOBJ, GOBEACC, SPRIDEN, PEBEMPL
-- SEVERITY: INFO
-- DESCRIPTION: For every Banner user who has been granted access to a Finance-module form, lists the user, the form, the role, and HOW the access was granted (class, direct, group). Two-part output: (1) detail row per (user, form, role), (2) summary row per user with a comma-delimited list of all Finance forms they can reach.
-- WHEN_TO_USE: Business-office access reviews ('who can run our POs?'). Manager requests of the form 'tell me which screens my team can see'. Building Argos datablocks where a Finance supervisor self-filters by form or by role. To switch modules, change guraobj_sysi_code = 'F' to 'S' (Student), 'P' (HR/Payroll), 'A' (Advancement), 'R' (Financial Aid), 'T' (AR), 'G' (General).
-- CAVEATS: Uses GURAOBJ_SYSI_CODE to scope to Finance — if your site has objects missing this code, you may need a fallback (e.g. OR guvuacc_object LIKE 'F%'). 'User' here means a Banner account that currently has effective access; GUVUACC already unions class, direct, and group grants. Terminated employees still appear if their account hasn't been disabled — that's intentional (it's a finding, not a bug). The summary part uses LISTAGG which is 4000-byte-capped; a user with 600+ objects may truncate — split into multiple rows if that happens.

-- =====================================================
-- PART 1 — Detail: one row per (user, Finance form, role)
-- =====================================================
SELECT
    gu.guvuacc_user                                      AS username,
    ga.gobeacc_pidm                                      AS pidm,
    si.spriden_id                                        AS banner_id,
    si.spriden_first_name || ' ' || si.spriden_last_name AS full_name,
    pe.pebempl_term_date                                 AS employee_term_date,
    gu.guvuacc_object                                    AS banner_form,
    gu.guvuacc_role                                      AS role_name,
    CASE
        WHEN gu.guvuacc_role LIKE '%\_Q' ESCAPE '\' THEN 'Query'
        WHEN gu.guvuacc_role LIKE '%\_M' ESCAPE '\' THEN 'Maintenance'
        WHEN gu.guvuacc_role LIKE '%\_B' ESCAPE '\' THEN 'Both'
        WHEN gu.guvuacc_role LIKE '%\_U' ESCAPE '\' THEN 'Update'
        ELSE 'Other/Custom'
    END                                                  AS access_level,
    gu.guvuacc_type                                      AS access_via,
    gu.guvuacc_class                                     AS via_class
FROM        bansecr.guvuacc gu
INNER JOIN  bansecr.guraobj ao ON ao.guraobj_object     = gu.guvuacc_object
LEFT JOIN   general.gobeacc ga ON ga.gobeacc_username  = gu.guvuacc_user
LEFT JOIN   spriden si         ON si.spriden_pidm      = ga.gobeacc_pidm
                              AND si.spriden_change_ind IS NULL
                              AND si.spriden_entity_ind = 'P'
LEFT JOIN   pebempl pe         ON pe.pebempl_pidm      = ga.gobeacc_pidm
WHERE       ao.guraobj_sysi_code = 'F'
ORDER BY    gu.guvuacc_user, gu.guvuacc_object;


-- =====================================================
-- PART 2 — Summary: one row per user with aggregated form list
-- =====================================================
SELECT
    gu.guvuacc_user                                      AS username,
    si.spriden_first_name || ' ' || si.spriden_last_name AS full_name,
    COUNT(DISTINCT gu.guvuacc_object)                    AS finance_form_count,
    COUNT(CASE WHEN gu.guvuacc_role LIKE '%\_M' ESCAPE '\' THEN 1 END) AS maintenance_count,
    COUNT(CASE WHEN gu.guvuacc_role LIKE '%\_Q' ESCAPE '\' THEN 1 END) AS query_count,
    COUNT(CASE WHEN gu.guvuacc_type = 'Class'  THEN 1 END) AS via_class_count,
    COUNT(CASE WHEN gu.guvuacc_type = 'Direct' THEN 1 END) AS via_direct_count,
    LISTAGG(DISTINCT gu.guvuacc_object, ', ')
        WITHIN GROUP (ORDER BY gu.guvuacc_object)        AS finance_forms,
    MAX(pe.pebempl_term_date)                            AS employee_term_date
FROM        bansecr.guvuacc gu
INNER JOIN  bansecr.guraobj ao ON ao.guraobj_object     = gu.guvuacc_object
LEFT JOIN   general.gobeacc ga ON ga.gobeacc_username  = gu.guvuacc_user
LEFT JOIN   spriden si         ON si.spriden_pidm      = ga.gobeacc_pidm
                              AND si.spriden_change_ind IS NULL
                              AND si.spriden_entity_ind = 'P'
LEFT JOIN   pebempl pe         ON pe.pebempl_pidm      = ga.gobeacc_pidm
WHERE       ao.guraobj_sysi_code = 'F'
GROUP BY    gu.guvuacc_user, si.spriden_first_name, si.spriden_last_name
ORDER BY    finance_form_count DESC, gu.guvuacc_user;

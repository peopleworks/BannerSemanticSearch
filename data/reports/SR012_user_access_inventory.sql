-- REPORT_ID: SR012
-- TITLE: Banner User Access Inventory — Finance Module (with friendly names)
-- CATEGORY: Inventory
-- TABLES: GUVUACC, GURAOBJ, GUBOBJS (GENERAL), GUBROLE, GOBEACC, SPRIDEN, PEBEMPL
-- SEVERITY: INFO
-- DESCRIPTION: For every Banner user who has been granted access to a Finance-module form, lists the user, the form (with its human-readable description from GUBOBJS), the role (with its human-readable comments from GUBROLE), HOW the access was granted, and whether that role carries write permission. Two-part output: (1) detail row per (user, form, role), (2) summary row per user with a comma-delimited list of all Finance forms they can reach.
-- WHEN_TO_USE: Business-office access reviews ('who can run our POs?'). Manager requests of the form 'tell me which screens my team can see' — now readable because every form code is paired with its plain-English description. Building Argos datablocks where a Finance supervisor self-filters by form or by role. To switch modules, change guraobj_sysi_code = 'F' to 'S' (Student), 'P' (HR/Payroll), 'A' (Advancement), 'R' (Financial Aid), 'T' (AR), 'G' (General).
-- CAVEATS: GUBOBJS lives in the GENERAL schema at most Banner sites (not BANSECR) — if yours is different, change the prefix on that JOIN. GUBOBJS_DESC is populated for baseline Banner forms; custom forms may show NULL descriptions (the code still appears in banner_form). GUBROLE_COMMENTS is often sparse or empty, which is why we also derive an access_description column from the role suffix (_Q/_M/_B/_U). The GUBROLE_MOD_ACCESS_IND flag is the authoritative Y/N for whether the role can write — trust it over the suffix when they disagree. Uses GURAOBJ_SYSI_CODE to scope to Finance. Terminated employees still appear if their account hasn't been disabled — that's intentional. Summary LISTAGGs use ON OVERFLOW TRUNCATE so a power-user with 600+ forms gets the list clipped with '...(NNN)' instead of an ORA-01489 (Oracle 12.2+ required; on older versions remove the ON OVERFLOW clause and expect truncation errors at the 4000-byte boundary).

-- =====================================================
-- PART 1 — Detail: one row per (user, Finance form, role) with friendly names
-- =====================================================
SELECT
    gu.guvuacc_user                                      AS username,
    ga.gobeacc_pidm                                      AS pidm,
    si.spriden_id                                        AS banner_id,
    si.spriden_first_name || ' ' || si.spriden_last_name AS full_name,
    pe.pebempl_term_date                                 AS employee_term_date,
    gu.guvuacc_object                                    AS banner_form,
    fo.gubobjs_desc                                      AS form_description,
    gu.guvuacc_role                                      AS role_name,
    ro.gubrole_comments                                  AS role_description,
    CASE
        WHEN gu.guvuacc_role LIKE '%\_Q' ESCAPE '\' THEN 'Query (read-only)'
        WHEN gu.guvuacc_role LIKE '%\_M' ESCAPE '\' THEN 'Maintenance (read + write)'
        WHEN gu.guvuacc_role LIKE '%\_B' ESCAPE '\' THEN 'Both (query + maintenance)'
        WHEN gu.guvuacc_role LIKE '%\_U' ESCAPE '\' THEN 'Update (write)'
        ELSE 'Other / custom role — review'
    END                                                  AS access_description,
    NVL(ro.gubrole_mod_access_ind, 'N')                  AS can_write_flag,
    gu.guvuacc_type                                      AS access_via,
    gu.guvuacc_class                                     AS via_class
FROM        bansecr.guvuacc gu
INNER JOIN  bansecr.guraobj ao ON ao.guraobj_object     = gu.guvuacc_object
LEFT JOIN   general.gubobjs fo ON fo.gubobjs_name       = gu.guvuacc_object
LEFT JOIN   bansecr.gubrole ro ON ro.gubrole_role       = gu.guvuacc_role
LEFT JOIN   general.gobeacc ga ON ga.gobeacc_username  = gu.guvuacc_user
LEFT JOIN   spriden si         ON si.spriden_pidm      = ga.gobeacc_pidm
                              AND si.spriden_change_ind IS NULL
                              AND si.spriden_entity_ind = 'P'
LEFT JOIN   pebempl pe         ON pe.pebempl_pidm      = ga.gobeacc_pidm
WHERE       ao.guraobj_sysi_code = 'F'
ORDER BY    gu.guvuacc_user, gu.guvuacc_object;


-- =====================================================
-- PART 2 — Summary: one row per user with aggregated form list (with descriptions)
-- =====================================================
SELECT
    gu.guvuacc_user                                      AS username,
    si.spriden_first_name || ' ' || si.spriden_last_name AS full_name,
    COUNT(DISTINCT gu.guvuacc_object)                    AS finance_form_count,
    COUNT(CASE WHEN gu.guvuacc_role LIKE '%\_M' ESCAPE '\' THEN 1 END) AS maintenance_count,
    COUNT(CASE WHEN gu.guvuacc_role LIKE '%\_Q' ESCAPE '\' THEN 1 END) AS query_count,
    COUNT(CASE WHEN NVL(ro.gubrole_mod_access_ind,'N')='Y' THEN 1 END) AS write_capable_count,
    COUNT(CASE WHEN gu.guvuacc_type = 'Class'  THEN 1 END) AS via_class_count,
    COUNT(CASE WHEN gu.guvuacc_type = 'Direct' THEN 1 END) AS via_direct_count,
    LISTAGG(DISTINCT gu.guvuacc_object, ', ' ON OVERFLOW TRUNCATE '...' WITH COUNT)
        WITHIN GROUP (ORDER BY gu.guvuacc_object)        AS finance_forms,
    LISTAGG(DISTINCT gu.guvuacc_object || ' — ' || NVL(fo.gubobjs_desc,'(no description)'),
            ' | ' ON OVERFLOW TRUNCATE '...' WITH COUNT)
        WITHIN GROUP (ORDER BY gu.guvuacc_object)        AS finance_forms_with_descriptions,
    MAX(pe.pebempl_term_date)                            AS employee_term_date
FROM        bansecr.guvuacc gu
INNER JOIN  bansecr.guraobj ao ON ao.guraobj_object     = gu.guvuacc_object
LEFT JOIN   general.gubobjs fo ON fo.gubobjs_name       = gu.guvuacc_object
LEFT JOIN   bansecr.gubrole ro ON ro.gubrole_role       = gu.guvuacc_role
LEFT JOIN   general.gobeacc ga ON ga.gobeacc_username  = gu.guvuacc_user
LEFT JOIN   spriden si         ON si.spriden_pidm      = ga.gobeacc_pidm
                              AND si.spriden_change_ind IS NULL
                              AND si.spriden_entity_ind = 'P'
LEFT JOIN   pebempl pe         ON pe.pebempl_pidm      = ga.gobeacc_pidm
WHERE       ao.guraobj_sysi_code = 'F'
GROUP BY    gu.guvuacc_user, si.spriden_first_name, si.spriden_last_name
ORDER BY    finance_form_count DESC, gu.guvuacc_user;

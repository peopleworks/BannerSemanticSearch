-- REPORT_ID: SR008
-- TITLE: Super Users — top holders of maintenance-level grants
-- CATEGORY: Privilege Escalation Risk
-- TABLES: GURUOBJ, GOBEACC, SPRIDEN, GUVUACC
-- SEVERITY: HIGH
-- DESCRIPTION: Users with the most direct GURUOBJ grants at the _M (maintenance/write) level. These are effectively your Banner 'super users' — the ones who can modify data across the most objects. Pair with total effective object access from GUVUACC to see the full picture.
-- WHEN_TO_USE: Annual privileged-access review. This list is what auditors mean when they ask 'who are your most powerful users?'. Expect: DBAs, Banner module admins, senior functional users. RED FLAG: anyone here who doesn't have a formal administrator role documented with HR.
-- CAVEATS: The _M suffix detection covers ~99.97% of WCC roles but misses 3 custom roles (BAN_DEFAULT_NO_ACCESS etc.). Users with only class-based maintenance access won't appear here — this report is specifically about DIRECT grants that bypass the class model. For full effective access including class-based, use SR010 or a GUVUACC-based custom query.

SELECT
    go.guruobj_userid                                    AS username,
    ga.gobeacc_pidm                                      AS pidm,
    si.spriden_first_name || ' ' || si.spriden_last_name AS full_name,
    COUNT(CASE WHEN go.guruobj_role LIKE '%\_M' ESCAPE '\' THEN 1 END) AS maintenance_grants,
    COUNT(CASE WHEN go.guruobj_role LIKE '%\_Q' ESCAPE '\' THEN 1 END) AS query_grants,
    COUNT(CASE WHEN go.guruobj_role LIKE '%\_B' ESCAPE '\' THEN 1 END) AS both_grants,
    COUNT(*)                                             AS total_direct_grants,
    (SELECT COUNT(DISTINCT gu.guvuacc_object)
       FROM bansecr.guvuacc gu
      WHERE gu.guvuacc_user = go.guruobj_userid)         AS total_effective_objects,
    pe.pebempl_term_date                                 AS employee_term_date
FROM        bansecr.guruobj go
LEFT JOIN   general.gobeacc ga ON ga.gobeacc_username = go.guruobj_userid
LEFT JOIN   spriden si         ON si.spriden_pidm     = ga.gobeacc_pidm
                              AND si.spriden_change_ind IS NULL
                              AND si.spriden_entity_ind = 'P'
LEFT JOIN   pebempl pe         ON pe.pebempl_pidm     = ga.gobeacc_pidm
GROUP BY    go.guruobj_userid, ga.gobeacc_pidm,
            si.spriden_first_name, si.spriden_last_name, pe.pebempl_term_date
HAVING      COUNT(CASE WHEN go.guruobj_role LIKE '%\_M' ESCAPE '\' THEN 1 END) >= 5
ORDER BY    maintenance_grants DESC, total_effective_objects DESC
FETCH FIRST 25 ROWS ONLY;

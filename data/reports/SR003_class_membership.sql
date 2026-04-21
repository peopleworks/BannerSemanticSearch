-- REPORT_ID: SR003
-- TITLE: Class Membership Report
-- CATEGORY: Access Review
-- TABLES: GURACLS, GTVCLAS, GOBEACC, SPRIDEN
-- SEVERITY: INFO
-- DESCRIPTION: The canonical 'who belongs to which class today' query with correct audit_time MAX() subquery and audit_action filter. This is the baseline for every class-level access review — the one you hand to an auditor who asks 'show me who has class X'.
-- WHEN_TO_USE: Any class-level access review. Pivot the output by class_code for 'who is in this class' or by userid for 'what classes does this user have'. For a user-centric view, use SR004 (direct grants) to spot bypasses.
-- CAVEATS: Covers the modern GURACLS table (~19K active assignments at WCC). WCC also has GURUCLS populated with 7,582 legacy rows — for a TRULY complete picture, UNION both. The GUVUACC view is a shortcut if you don't need audit_time, but it won't show you 'when' the grant happened.

SELECT
    gc.guracls_userid                                    AS username,
    ga.gobeacc_pidm                                      AS pidm,
    si.spriden_id                                        AS banner_id,
    si.spriden_first_name || ' ' || si.spriden_last_name AS full_name,
    gc.guracls_class_code                                AS class_code,
    tc.gtvclas_comments                                  AS class_description,
    gc.guracls_audit_time                                AS granted_on,
    gc.guracls_activity_date                             AS last_activity
FROM        bansecr.guracls gc
LEFT JOIN   general.gobeacc ga ON ga.gobeacc_username = gc.guracls_userid
LEFT JOIN   spriden si         ON si.spriden_pidm     = ga.gobeacc_pidm
                              AND si.spriden_change_ind IS NULL
                              AND si.spriden_entity_ind = 'P'
LEFT JOIN   bansecr.gtvclas tc ON tc.gtvclas_class_code = gc.guracls_class_code
WHERE  gc.guracls_audit_time =
           (SELECT MAX(g2.guracls_audit_time)
              FROM bansecr.guracls g2
             WHERE g2.guracls_userid     = gc.guracls_userid
               AND g2.guracls_class_code = gc.guracls_class_code)
  AND  gc.guracls_audit_action <> 'D'
ORDER BY gc.guracls_userid, gc.guracls_class_code;

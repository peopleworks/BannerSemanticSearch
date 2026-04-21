-- REPORT_ID: SR002
-- TITLE: Terminated Employees with Active Banner Access
-- CATEGORY: Access Review
-- TABLES: PEBEMPL, GOBEACC, GURACLS, GUVUACC, SPRIDEN, GURLOGN
-- SEVERITY: HIGH
-- DESCRIPTION: Employees whose PEBEMPL_TERM_DATE is in the past and who still have active class assignments or object access in Banner. This is the #1 finding every auditor looks for and the most common control failure in access reviews.
-- WHEN_TO_USE: Monthly (minimum). Any non-empty result set requires immediate offboarding cleanup. File the output as SOX/FERPA evidence. Also share with the HR-to-IT offboarding workflow team to find where the handoff is breaking.
-- CAVEATS: Terminations processed the same day may not yet be reflected. Verify WCC's grace-period policy (commonly 7-30 days post-term for benefits close-out, COBRA paperwork, etc.). The days_since_term column helps filter out legitimate in-grace cases. Cross-check with HR before disabling access — some 'terminated' employees are in rehire pipeline.

SELECT
    pe.pebempl_pidm                                      AS pidm,
    si.spriden_id                                        AS banner_id,
    si.spriden_first_name || ' ' || si.spriden_last_name AS full_name,
    ga.gobeacc_username                                  AS username,
    pe.pebempl_term_date                                 AS terminated_on,
    TRUNC(SYSDATE - pe.pebempl_term_date)                AS days_since_term,
    (SELECT COUNT(*)
       FROM bansecr.guracls gc
      WHERE gc.guracls_userid       = ga.gobeacc_username
        AND gc.guracls_audit_action <> 'D'
        AND gc.guracls_audit_time   =
            (SELECT MAX(g2.guracls_audit_time)
               FROM bansecr.guracls g2
              WHERE g2.guracls_userid     = gc.guracls_userid
                AND g2.guracls_class_code = gc.guracls_class_code))   AS active_class_count,
    (SELECT COUNT(DISTINCT guvuacc_object)
       FROM bansecr.guvuacc
      WHERE guvuacc_user = ga.gobeacc_username)                       AS object_access_count,
    (SELECT MAX(gl.gurlogn_last_logon_date)
       FROM bansecr.gurlogn gl
      WHERE gl.gurlogn_user = ga.gobeacc_username)                    AS last_logon
FROM       pebempl pe
JOIN       general.gobeacc ga ON ga.gobeacc_pidm = pe.pebempl_pidm
JOIN       spriden si         ON si.spriden_pidm = pe.pebempl_pidm
                             AND si.spriden_change_ind IS NULL
                             AND si.spriden_entity_ind = 'P'
WHERE  pe.pebempl_term_date IS NOT NULL
  AND  pe.pebempl_term_date < SYSDATE
  AND  EXISTS (SELECT 1
                 FROM bansecr.guracls gc
                WHERE gc.guracls_userid       = ga.gobeacc_username
                  AND gc.guracls_audit_action <> 'D'
                  AND gc.guracls_audit_time   =
                      (SELECT MAX(g2.guracls_audit_time)
                         FROM bansecr.guracls g2
                        WHERE g2.guracls_userid     = gc.guracls_userid
                          AND g2.guracls_class_code = gc.guracls_class_code))
ORDER BY pe.pebempl_term_date;

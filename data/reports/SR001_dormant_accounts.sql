-- REPORT_ID: SR001
-- TITLE: Dormant Banner Accounts
-- CATEGORY: Access Review
-- TABLES: GOBEACC, GURLOGN, SPRIDEN, PEBEMPL, GURACLS
-- SEVERITY: MEDIUM
-- DESCRIPTION: Banner accounts that have never logged in OR have not logged in for 180+ days across any access path (Oracle direct, Banner INB, or Web/Horizon).
-- WHEN_TO_USE: Quarterly access review; offboarding audit; SOX evidence of dormant-account cleanup. Pairs well with SR002 (terminated-with-access).
-- CAVEATS: GURLOGN_*_LAST_LOGON_DATE only updates if the database trigger GT_GURALGN_AUDIT_LOGON is active (confirmed enabled at WCC — 86M GURALGN rows). Users who authenticate only via SSO/Luminis without hitting Oracle directly may appear dormant even if active. Service accounts typically surface here — exclude known ones via a whitelist if needed.

SELECT
    ga.gobeacc_username                                  AS username,
    ga.gobeacc_pidm                                      AS pidm,
    si.spriden_id                                        AS banner_id,
    si.spriden_first_name || ' ' || si.spriden_last_name AS full_name,
    gl.gurlogn_first_logon_date                          AS first_logon,
    gl.gurlogn_last_logon_date                           AS last_oracle_logon,
    gl.gurlogn_inb_last_logon_date                       AS last_inb_logon,
    gl.gurlogn_hrzn_last_logon_date                      AS last_web_logon,
    CASE
        WHEN gl.gurlogn_last_logon_date       IS NULL
         AND gl.gurlogn_inb_last_logon_date   IS NULL
         AND gl.gurlogn_hrzn_last_logon_date  IS NULL
        THEN 'NEVER LOGGED IN'
        ELSE TO_CHAR(TRUNC(SYSDATE -
            GREATEST(NVL(gl.gurlogn_last_logon_date,      DATE '1900-01-01'),
                     NVL(gl.gurlogn_inb_last_logon_date,  DATE '1900-01-01'),
                     NVL(gl.gurlogn_hrzn_last_logon_date, DATE '1900-01-01')))) || ' days since last login'
    END                                                  AS status,
    pe.pebempl_term_date                                 AS employee_term_date,
    (SELECT COUNT(*)
       FROM bansecr.guracls gc
      WHERE gc.guracls_userid      = ga.gobeacc_username
        AND gc.guracls_audit_action <> 'D'
        AND gc.guracls_audit_time   =
            (SELECT MAX(g2.guracls_audit_time)
               FROM bansecr.guracls g2
              WHERE g2.guracls_userid     = gc.guracls_userid
                AND g2.guracls_class_code = gc.guracls_class_code))   AS active_class_count
FROM        general.gobeacc ga
LEFT JOIN   bansecr.gurlogn gl ON gl.gurlogn_user   = ga.gobeacc_username
LEFT JOIN   spriden si         ON si.spriden_pidm   = ga.gobeacc_pidm
                              AND si.spriden_change_ind IS NULL
                              AND si.spriden_entity_ind = 'P'
LEFT JOIN   pebempl pe         ON pe.pebempl_pidm   = ga.gobeacc_pidm
WHERE  (gl.gurlogn_last_logon_date      IS NULL OR gl.gurlogn_last_logon_date      < SYSDATE - 180)
  AND  (gl.gurlogn_inb_last_logon_date  IS NULL OR gl.gurlogn_inb_last_logon_date  < SYSDATE - 180)
  AND  (gl.gurlogn_hrzn_last_logon_date IS NULL OR gl.gurlogn_hrzn_last_logon_date < SYSDATE - 180)
ORDER BY
    gl.gurlogn_last_logon_date NULLS FIRST,
    ga.gobeacc_username;

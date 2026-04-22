-- REPORT_ID: SR014
-- TITLE: Banner Security Posture Scorecard (one-row dashboard feed)
-- CATEGORY: Monitoring
-- TABLES: GOBEACC, GURLOGN, PEBEMPL, GURACLS, GURUOBJ, GUVUACC, GURALOG, GTVCLAS, GURUCLS
-- SEVERITY: INFO
-- DESCRIPTION: A single SELECT that returns ONE row with every key metric used by the Security Posture dashboard card in this tool. Run this in Argos or SQL Developer, copy the output row (tab/pipe/comma-delimited — with or without headers), paste it into the "Security Posture" view of this app, and the dashboard paints itself with traffic-light gauges: Dormant, Terminated w/ Access, Super Users, Direct Grants, PII Broad Access, Violations, Unused Classes, Legacy GURUCLS, plus baseline totals.
-- WHEN_TO_USE: Monthly — paste one new row into the scorecard each month and track trends. Before every audit meeting — print-preview the scorecard page and bring it as cover sheet. After every big access change — run this and the scorecard to see if any metric jumped into the red.
-- CAVEATS: Every sub-metric uses the same logic as its corresponding SR0XX report — no drift, no surprises. Numbers are a point-in-time snapshot at SYSDATE; thresholds for green/yellow/red are embedded in the dashboard UI and calibrated for a mid-sized Banner site (≈5K accounts). Institutions larger or smaller should tune the thresholds in the scorecard view if the colors don't feel right. The query uses correlated subqueries (the audit_time MAX pattern) so expect ~2–5 seconds on a ~20K GURACLS table — completely acceptable.

SELECT
    -- ======  Baseline denominators  ======
    (SELECT COUNT(*) FROM general.gobeacc)                 AS total_accounts,
    (SELECT COUNT(DISTINCT guvuacc_user)
       FROM bansecr.guvuacc)                               AS users_with_access,
    (SELECT COUNT(*) FROM bansecr.guvuacc)                 AS total_effective_grants,

    -- ======  SR001: Dormant accounts (no logon 180+ days on any path)  ======
    (SELECT COUNT(*)
       FROM general.gobeacc ga
       LEFT JOIN bansecr.gurlogn gl ON gl.gurlogn_user = ga.gobeacc_username
      WHERE (gl.gurlogn_last_logon_date      IS NULL OR gl.gurlogn_last_logon_date      < SYSDATE - 180)
        AND (gl.gurlogn_inb_last_logon_date  IS NULL OR gl.gurlogn_inb_last_logon_date  < SYSDATE - 180)
        AND (gl.gurlogn_hrzn_last_logon_date IS NULL OR gl.gurlogn_hrzn_last_logon_date < SYSDATE - 180)
    )                                                      AS dormant_accounts,

    -- ======  SR002: Terminated employees with active access  ======
    (SELECT COUNT(DISTINCT pe.pebempl_pidm)
       FROM pebempl pe
       JOIN general.gobeacc ga ON ga.gobeacc_pidm = pe.pebempl_pidm
      WHERE pe.pebempl_term_date IS NOT NULL
        AND pe.pebempl_term_date < SYSDATE
        AND EXISTS (SELECT 1 FROM bansecr.guracls gc
                     WHERE gc.guracls_userid       = ga.gobeacc_username
                       AND gc.guracls_audit_action <> 'D'
                       AND gc.guracls_audit_time   =
                           (SELECT MAX(g2.guracls_audit_time)
                              FROM bansecr.guracls g2
                             WHERE g2.guracls_userid     = gc.guracls_userid
                               AND g2.guracls_class_code = gc.guracls_class_code))
    )                                                      AS terminated_with_access,

    -- ======  SR004: Users with 10+ direct grants (bypassing CLASS model)  ======
    (SELECT COUNT(*) FROM (
        SELECT guruobj_userid
          FROM bansecr.guruobj
         GROUP BY guruobj_userid
        HAVING COUNT(*) >= 10
    ))                                                     AS users_bypassing_classes,

    -- ======  SR008: Super users — 5+ maintenance-level direct grants  ======
    (SELECT COUNT(*) FROM (
        SELECT guruobj_userid
          FROM bansecr.guruobj
         WHERE guruobj_role LIKE '%\_M' ESCAPE '\'
         GROUP BY guruobj_userid
        HAVING COUNT(*) >= 5
    ))                                                     AS super_users,

    -- ======  SR011: PII broad access — 5+ sensitive objects  ======
    (SELECT COUNT(*) FROM (
        SELECT guvuacc_user
          FROM bansecr.guvuacc
         WHERE guvuacc_object IN ('SPAIDEN','SOAIDEN','SPAAPIN','SPACMNT',
                                  'PPAIDEN','GOAINTL','PPAGENL','SPBPERS')
         GROUP BY guvuacc_user
        HAVING COUNT(DISTINCT guvuacc_object) >= 5
    ))                                                     AS pii_broad_users,

    -- ======  SR005: Security violations last 30 days  ======
    (SELECT COUNT(*) FROM bansecr.guralog
      WHERE guralog_activity_date >= SYSDATE - 30)         AS violations_30d,

    -- ======  SR006: Unused security classes (cleanup candidates)  ======
    (SELECT COUNT(*)
       FROM bansecr.gtvclas tc
      WHERE NOT EXISTS (SELECT 1 FROM bansecr.guracls gc
                         WHERE gc.guracls_class_code   = tc.gtvclas_class_code
                           AND gc.guracls_audit_action <> 'D'
                           AND gc.guracls_audit_time   =
                               (SELECT MAX(g2.guracls_audit_time)
                                  FROM bansecr.guracls g2
                                 WHERE g2.guracls_userid     = gc.guracls_userid
                                   AND g2.guracls_class_code = gc.guracls_class_code))
    )                                                      AS unused_classes,

    -- ======  Technical debt: legacy GURUCLS rows still populated  ======
    (SELECT COUNT(*) FROM bansecr.gurucls)                 AS legacy_gurucls_rows,

    -- ======  SR009: Access changes last 30 days (rate of change)  ======
    (SELECT COUNT(*) FROM bansecr.guracls
      WHERE guracls_audit_time >= SYSDATE - 30)            AS access_changes_30d,

    -- ======  Timestamp of this scorecard  ======
    TO_CHAR(SYSDATE, 'YYYY-MM-DD HH24:MI')                 AS snapshot_taken_at
FROM dual;

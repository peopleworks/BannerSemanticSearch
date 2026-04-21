-- REPORT_ID: SR005
-- TITLE: Security Violation Dashboard (last 30 days)
-- CATEGORY: Monitoring
-- TABLES: GURALOG, GOBEACC, SPRIDEN
-- SEVERITY: INFO
-- DESCRIPTION: Two-part dashboard of Banner security violations from GURALOG in the last 30 days: (1) summary grouped by reason with counts and severity, (2) top offenders with 5+ violations.
-- WHEN_TO_USE: Weekly security monitoring, or when spikes in specific error classes warrant investigation. A single user recurring at the top is a strong indicator of either an automation misconfiguration (service account hitting a forbidden form repeatedly) or an attempt to escalate.
-- CAVEATS: GURALOG at WCC holds 233K total violations growing ~26/day. GURALOG_SEVERITY_LEVEL rates importance (1 = highest) — filter on severity for triage. Test/dev schema violations also surface here; consider adding WHERE guralog_userid NOT LIKE '%_TEST' etc. if your environment has a pattern. Run both parts together; they're complementary.

-- =====================================================
-- PART 1 — Summary: top violation reasons in last 30 days
-- =====================================================
SELECT
    guralog_reason                 AS violation_reason,
    COUNT(*)                       AS count_last_30d,
    COUNT(DISTINCT guralog_userid) AS distinct_users,
    MIN(guralog_activity_date)     AS first_seen,
    MAX(guralog_activity_date)     AS last_seen,
    MIN(guralog_severity_level)    AS worst_severity
FROM       bansecr.guralog
WHERE      guralog_activity_date >= SYSDATE - 30
GROUP BY   guralog_reason
ORDER BY   count_last_30d DESC;


-- =====================================================
-- PART 2 — Top offenders: users with 5+ violations
-- =====================================================
SELECT
    gl.guralog_userid                                    AS username,
    si.spriden_first_name || ' ' || si.spriden_last_name AS full_name,
    COUNT(*)                                             AS violation_count,
    COUNT(DISTINCT gl.guralog_object)                    AS distinct_objects,
    COUNT(DISTINCT gl.guralog_reason)                    AS distinct_reasons,
    MIN(gl.guralog_severity_level)                       AS worst_severity,
    MAX(gl.guralog_activity_date)                        AS most_recent
FROM        bansecr.guralog gl
LEFT JOIN   general.gobeacc ga ON ga.gobeacc_username = gl.guralog_userid
LEFT JOIN   spriden si         ON si.spriden_pidm     = ga.gobeacc_pidm
                              AND si.spriden_change_ind IS NULL
                              AND si.spriden_entity_ind = 'P'
WHERE       gl.guralog_activity_date >= SYSDATE - 30
GROUP BY    gl.guralog_userid, si.spriden_first_name, si.spriden_last_name
HAVING      COUNT(*) >= 5
ORDER BY    violation_count DESC
FETCH FIRST 25 ROWS ONLY;

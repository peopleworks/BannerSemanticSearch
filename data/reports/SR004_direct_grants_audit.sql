-- REPORT_ID: SR004
-- TITLE: Direct Object Grants — Users Bypassing the CLASS Model
-- CATEGORY: Privilege Escalation Risk
-- TABLES: GURUOBJ, GOBEACC, SPRIDEN
-- SEVERITY: HIGH
-- DESCRIPTION: Users who have accumulated direct object grants in GURUOBJ. These grants bypass the CLASS-based access model — each one is an exception that should have been justified, time-boxed, and reviewed. In practice, they accumulate and become invisible privilege creep.
-- WHEN_TO_USE: Quarterly privilege review, or whenever an auditor asks about least-privilege controls. Users at the top of the list fall into three buckets: (a) legitimate power users (DBAs, application developers), (b) historical accumulations that need cleanup, (c) actual over-privileged accounts. All three merit a documented justification per user.
-- CAVEATS: The access-level interpretation via role suffix (_Q=Query, _M=Maintenance, _B=Both, _U=Update) works for 99.97% of rows at WCC (12,093 of 12,096). The 'custom_role_grants' column captures the 3 edge cases with custom Banner roles (BAN_DEFAULT_NO_ACCESS, _CONNECT, _CMQUERYEXECUTE_HR) plus any similar anomalies — these need separate interpretation via GUBROLE or GURAOBJ_DEFAULT_ROLE.

SELECT
    go.guruobj_userid                                    AS username,
    ga.gobeacc_pidm                                      AS pidm,
    si.spriden_first_name || ' ' || si.spriden_last_name AS full_name,
    COUNT(*)                                             AS direct_grant_count,
    COUNT(CASE WHEN go.guruobj_role LIKE '%\_M' ESCAPE '\' THEN 1 END) AS maintenance_grants,
    COUNT(CASE WHEN go.guruobj_role LIKE '%\_Q' ESCAPE '\' THEN 1 END) AS query_grants,
    COUNT(CASE WHEN go.guruobj_role LIKE '%\_B' ESCAPE '\' THEN 1 END) AS both_grants,
    COUNT(CASE WHEN go.guruobj_role LIKE '%\_U' ESCAPE '\' THEN 1 END) AS update_grants,
    COUNT(CASE WHEN go.guruobj_role NOT LIKE '%\_Q' ESCAPE '\'
                AND go.guruobj_role NOT LIKE '%\_M' ESCAPE '\'
                AND go.guruobj_role NOT LIKE '%\_B' ESCAPE '\'
                AND go.guruobj_role NOT LIKE '%\_U' ESCAPE '\'
               THEN 1 END)                               AS custom_role_grants
FROM       bansecr.guruobj go
LEFT JOIN  general.gobeacc ga ON ga.gobeacc_username = go.guruobj_userid
LEFT JOIN  spriden si         ON si.spriden_pidm     = ga.gobeacc_pidm
                             AND si.spriden_change_ind IS NULL
                             AND si.spriden_entity_ind = 'P'
GROUP BY   go.guruobj_userid, ga.gobeacc_pidm,
           si.spriden_first_name, si.spriden_last_name
HAVING     COUNT(*) >= 10
ORDER BY   direct_grant_count DESC;

-- REPORT_ID: SR010
-- TITLE: Object Access Concentration (most-exposed Banner objects)
-- CATEGORY: Inventory
-- TABLES: GUVUACC, GURAOBJ
-- SEVERITY: MEDIUM
-- DESCRIPTION: Banner objects ranked by the number of distinct users with effective access. The top of the list identifies your most exposed forms/pages — these are the ones where one misconfigured class or group can affect the most people. Broken down by access path: Class-based vs Direct grants vs Group-based.
-- WHEN_TO_USE: Bi-annual inventory of 'what does everyone have access to?'. Critical for identifying forms that should be tightly controlled but are currently widely accessible — typical candidates: forms that touch SSN, grades, financial aid awards, or payroll. Filter by system_code to scope to one module at a time.
-- CAVEATS: Many users accessing a benign lookup form (e.g., GTVCOUN for counties) is fine. Many users accessing a sensitive form (e.g., SPBPERS for SSN/DOB) is the finding. Always read this list WITH knowledge of which objects contain sensitive data. Pairs well with SR011 (PII-specific).

SELECT
    gu.guvuacc_object                                  AS object,
    ao.guraobj_sysi_code                               AS system_code,
    ao.guraobj_default_role                            AS default_role,
    COUNT(DISTINCT gu.guvuacc_user)                    AS distinct_users,
    COUNT(CASE WHEN gu.guvuacc_type = 'Class' THEN 1 END)         AS via_class,
    COUNT(CASE WHEN gu.guvuacc_type = 'Direct' THEN 1 END)        AS via_direct,
    COUNT(CASE WHEN gu.guvuacc_type LIKE 'Group%' THEN 1 END)     AS via_group,
    COUNT(CASE WHEN gu.guvuacc_role LIKE '%\_M' ESCAPE '\' THEN 1 END) AS write_capable_grants
FROM        bansecr.guvuacc gu
LEFT JOIN   bansecr.guraobj ao ON ao.guraobj_object = gu.guvuacc_object
GROUP BY    gu.guvuacc_object, ao.guraobj_sysi_code, ao.guraobj_default_role
HAVING      COUNT(DISTINCT gu.guvuacc_user) >= 50
ORDER BY    distinct_users DESC
FETCH FIRST 40 ROWS ONLY;

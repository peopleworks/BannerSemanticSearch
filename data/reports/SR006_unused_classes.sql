-- REPORT_ID: SR006
-- TITLE: Unused Security Classes (cleanup candidates)
-- CATEGORY: Access Review
-- TABLES: GTVCLAS, GURACLS, GUVUACC
-- SEVERITY: INFO
-- DESCRIPTION: Security classes defined in GTVCLAS that have ZERO active user assignments in GURACLS. These are either deprecated classes that were never cleaned up, placeholders, or classes created by mistake. Candidates for removal.
-- WHEN_TO_USE: Annual class catalog cleanup. Also run after a Banner upgrade to find classes delivered by Ellucian that your institution never used. Objects-accessible count helps distinguish 'orphan empty class' (0 objects too — safe to drop) from 'configured but unassigned' (has objects but no users — investigate why).
-- CAVEATS: A class may show as unused in GURACLS but still appear in legacy GURUCLS at WCC (7,582 rows still populated). Don't drop a class just because GURACLS is empty — check GURUCLS for the same class_code first. Also, classes tied to scheduled jobs or APIs may look idle but still matter.

SELECT
    tc.gtvclas_class_code     AS class_code,
    tc.gtvclas_comments       AS description,
    tc.gtvclas_sysi_code      AS system_code,
    tc.gtvclas_activity_date  AS last_touched,
    (SELECT COUNT(*) FROM bansecr.guvuacc gu
      WHERE gu.guvuacc_class = tc.gtvclas_class_code)   AS objects_accessible,
    (SELECT COUNT(*) FROM bansecr.gurucls uc
      WHERE uc.gurucls_class_code = tc.gtvclas_class_code) AS legacy_gurucls_rows
FROM bansecr.gtvclas tc
WHERE NOT EXISTS (
    SELECT 1
      FROM bansecr.guracls gc
     WHERE gc.guracls_class_code   = tc.gtvclas_class_code
       AND gc.guracls_audit_action <> 'D'
       AND gc.guracls_audit_time   =
           (SELECT MAX(g2.guracls_audit_time)
              FROM bansecr.guracls g2
             WHERE g2.guracls_userid     = gc.guracls_userid
               AND g2.guracls_class_code = gc.guracls_class_code))
ORDER BY tc.gtvclas_sysi_code NULLS LAST, tc.gtvclas_class_code;

-- REPORT_ID: SR007
-- TITLE: Most Populated Classes (biggest attack surfaces)
-- CATEGORY: Access Review
-- TABLES: GURACLS, GTVCLAS, GUVUACC
-- SEVERITY: MEDIUM
-- DESCRIPTION: Classes ranked by the number of active users currently assigned. The largest classes are typically either generic 'everyone' buckets (often fine) or over-broad exceptions that accumulated users over the years (often NOT fine). Pair the user count with the object count to triage: high users + high objects = biggest blast radius.
-- WHEN_TO_USE: Quarterly, as a triage view for access review. Start at the top of the list — if a class has 500 users AND grants 200 objects, that one conversation with the module owner saves you a thousand one-by-one reviews. Classes with fewer users but still substantial object counts are your next tier.
-- CAVEATS: A class is only as risky as the objects it grants. A 'STAFF_ALL' class with 800 users but 3 read-only lookup objects is low-risk. A 'SR_POWER_USER' class with 15 users but 400 write-capable objects is high-risk. Always read user_count × object_count in context.

SELECT
    gc.guracls_class_code               AS class_code,
    tc.gtvclas_comments                 AS description,
    tc.gtvclas_sysi_code                AS system_code,
    COUNT(DISTINCT gc.guracls_userid)   AS active_users,
    (SELECT COUNT(DISTINCT gu.guvuacc_object)
       FROM bansecr.guvuacc gu
      WHERE gu.guvuacc_class = gc.guracls_class_code)                      AS object_count,
    (SELECT COUNT(CASE WHEN gu.guvuacc_role LIKE '%\_M' ESCAPE '\' THEN 1 END)
       FROM bansecr.guvuacc gu
      WHERE gu.guvuacc_class = gc.guracls_class_code)                      AS write_capable_objects
FROM       bansecr.guracls gc
LEFT JOIN  bansecr.gtvclas tc ON tc.gtvclas_class_code = gc.guracls_class_code
WHERE      gc.guracls_audit_action <> 'D'
  AND      gc.guracls_audit_time    =
           (SELECT MAX(g2.guracls_audit_time)
              FROM bansecr.guracls g2
             WHERE g2.guracls_userid     = gc.guracls_userid
               AND g2.guracls_class_code = gc.guracls_class_code)
GROUP BY   gc.guracls_class_code, tc.gtvclas_comments, tc.gtvclas_sysi_code
ORDER BY   active_users DESC, object_count DESC
FETCH FIRST 30 ROWS ONLY;

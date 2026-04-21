-- REPORT_ID: SR009
-- TITLE: Recent Access Changes (last 30 days audit trail)
-- CATEGORY: Monitoring
-- TABLES: GURACLS, GURAUOB, GOBEACC, SPRIDEN
-- SEVERITY: INFO
-- DESCRIPTION: Two-part audit: (1) class-level grants/updates/revocations in the last 30 days from GURACLS, (2) direct object-grant changes from GURAUOB (the audit table for GURUOBJ). Who did what, to whom, when. This is the paper trail an auditor asks for.
-- WHEN_TO_USE: Monthly compliance review; or reactively, after a security incident, to see 'what access changed recently?'. Also useful during onboarding of a new module owner — shows the kind of changes their predecessor was making.
-- CAVEATS: guracls_user_id is the Oracle user that PERFORMED the change (often a Banner security admin, not the target user). guracls_userid is the target. Don't confuse them — they look nearly identical. The audit action codes are: I=Insert (access granted), U=Update (grant changed), D=Delete (access revoked).

-- =====================================================
-- PART 1 — Class-level changes (GURACLS audit trail)
-- =====================================================
SELECT
    gc.guracls_audit_time           AS changed_on,
    gc.guracls_audit_action         AS action,
    CASE gc.guracls_audit_action
         WHEN 'I' THEN 'GRANTED'
         WHEN 'U' THEN 'UPDATED'
         WHEN 'D' THEN 'REVOKED'
    END                             AS action_description,
    gc.guracls_userid               AS target_user,
    gc.guracls_class_code           AS class_code,
    tc.gtvclas_comments             AS class_description,
    gc.guracls_user_id              AS changed_by,
    gc.guracls_comments             AS notes
FROM        bansecr.guracls gc
LEFT JOIN   bansecr.gtvclas tc ON tc.gtvclas_class_code = gc.guracls_class_code
WHERE       gc.guracls_audit_time >= SYSDATE - 30
ORDER BY    gc.guracls_audit_time DESC;


-- =====================================================
-- PART 2 — Direct-grant changes (GURAUOB audit trail)
-- =====================================================
SELECT
    gu.gurauob_audit_time           AS changed_on,
    gu.gurauob_audit_action         AS action,
    CASE gu.gurauob_audit_action
         WHEN 'I' THEN 'GRANTED'
         WHEN 'U' THEN 'UPDATED'
         WHEN 'D' THEN 'REVOKED'
    END                             AS action_description,
    gu.gurauob_userid               AS target_user,
    gu.gurauob_object               AS object,
    gu.gurauob_role                 AS role,
    gu.gurauob_user_id              AS changed_by
FROM        bansecr.gurauob gu
WHERE       gu.gurauob_audit_time >= SYSDATE - 30
ORDER BY    gu.gurauob_audit_time DESC;

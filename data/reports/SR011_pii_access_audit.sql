-- REPORT_ID: SR011
-- TITLE: PII / Sensitive Data Access Audit (SSN, DOB, demographics)
-- CATEGORY: Privilege Escalation Risk
-- TABLES: GUVUACC, GOBEACC, SPRIDEN, PEBEMPL
-- SEVERITY: HIGH
-- DESCRIPTION: Every user with effective access to Banner objects that read or maintain SPBPERS-sourced data — SSN, birth date, gender, marital status, citizenship. These are FERPA/PII-critical accesses that should be restricted to HR, Registrar, Financial Aid, Payroll, and certified admins. Anyone else on this list merits a conversation.
-- WHEN_TO_USE: Annually for FERPA compliance evidence. Also run before/after any Banner upgrade in case new class assignments granted broader access than expected. Share filtered output (by user name) with HR/Registrar to validate that each access is justified by job role.
-- CAVEATS: The object list is the canonical PII surface for Waubonsee — adjust if you have custom forms that touch SPBPERS. Seeing a user with many PII objects isn't automatically a finding — Registrar staff need SPAIDEN+SOAIDEN to do their job. Seeing an IT user with full PII access IS a finding unless they're on the privileged admin roster. Cross-reference with PEBEMPL_JOBS to see if the person's job title matches the access.

SELECT
    gu.guvuacc_user                                      AS username,
    ga.gobeacc_pidm                                      AS pidm,
    si.spriden_first_name || ' ' || si.spriden_last_name AS full_name,
    pe.pebempl_term_date                                 AS employee_term_date,
    COUNT(DISTINCT gu.guvuacc_object)                    AS pii_object_count,
    LISTAGG(DISTINCT gu.guvuacc_object, ', ' ON OVERFLOW TRUNCATE '...' WITH COUNT)
        WITHIN GROUP (ORDER BY gu.guvuacc_object)        AS pii_objects,
    MAX(CASE WHEN gu.guvuacc_role LIKE '%\_M' ESCAPE '\' THEN 'Y' ELSE 'N' END) AS can_modify_pii
FROM        bansecr.guvuacc gu
LEFT JOIN   general.gobeacc ga ON ga.gobeacc_username = gu.guvuacc_user
LEFT JOIN   spriden si         ON si.spriden_pidm     = ga.gobeacc_pidm
                              AND si.spriden_change_ind IS NULL
                              AND si.spriden_entity_ind = 'P'
LEFT JOIN   pebempl pe         ON pe.pebempl_pidm     = ga.gobeacc_pidm
WHERE       gu.guvuacc_object IN (
                'SPAIDEN',    -- General Person Identification
                'SOAIDEN',    -- Identification search form
                'SPAAPIN',    -- Alternate PIN maintenance
                'SPACMNT',    -- Comments (can contain sensitive notes)
                'PPAIDEN',    -- HR side of identification
                'GOAINTL',    -- International information (passport, visa)
                'PPAGENL',    -- HR general person
                'SPBPERS'     -- Base personal info (if exposed)
            )
GROUP BY    gu.guvuacc_user, ga.gobeacc_pidm,
            si.spriden_first_name, si.spriden_last_name, pe.pebempl_term_date
ORDER BY    can_modify_pii DESC, pii_object_count DESC, gu.guvuacc_user;

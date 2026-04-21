-- ============================================================
-- BANNER SECURITY: Health-check (VS Code / Oracle-extension friendly)
--
-- Single SELECT returning one result grid. Built from tables that
-- we ALREADY confirmed exist in WCC BANSECR (from bansecr_tables.txt).
-- No SPOOL, no PL/SQL, no DBMS_OUTPUT -- just run and export the grid.
--
-- HOW TO SAVE THE OUTPUT:
--   1. Run this query (F5 or play button)
--   2. In the result panel: right-click > Export > CSV (or TSV)
--   3. Save as: data\security_health_check.txt
--
-- GOBEACC probes are separate at the bottom (run individually).
-- ============================================================

SELECT metric, val, note FROM (
  SELECT 'GURACLS_rows_active'  AS metric, COUNT(*) AS val,
         'User->class active (audit_action<>D)' AS note
    FROM bansecr.guracls WHERE guracls_audit_action<>'D'
  UNION ALL
  SELECT 'GURACLS_rows_total', COUNT(*), 'User->class incl. deleted audit rows'
    FROM bansecr.guracls
  UNION ALL
  SELECT 'GURUCLS_rows', COUNT(*), 'Legacy user->class (pre-9)'
    FROM bansecr.gurucls
  UNION ALL
  SELECT 'GURUOBJ_rows', COUNT(*), 'User->object direct grants (bypass class)'
    FROM bansecr.guruobj
  UNION ALL
  SELECT 'GURAOBJ_rows', COUNT(*), 'Object master + default role per object'
    FROM bansecr.guraobj
  UNION ALL
  SELECT 'GTVCLAS_rows', COUNT(*), 'Class-code validation table'
    FROM bansecr.gtvclas
  UNION ALL
  SELECT 'GTVSGRP_rows', COUNT(*), 'Security-group validation'
    FROM bansecr.gtvsgrp
  UNION ALL
  SELECT 'GURCROL_rows', COUNT(*), 'Custom roles defined at WCC'
    FROM bansecr.gurcrol
  UNION ALL
  SELECT 'GURBGRP_rows', COUNT(*), 'Business profiles in security group'
    FROM bansecr.gurbgrp
  UNION ALL
  SELECT 'GURCGRP_rows', COUNT(*), 'Classes in security group'
    FROM bansecr.gurcgrp
  UNION ALL
  SELECT 'GURUGRP_rows', COUNT(*), 'Users in security group'
    FROM bansecr.gurugrp
  UNION ALL
  SELECT 'GUROGRP_rows', COUNT(*), 'Objects in security group'
    FROM bansecr.gurogrp
  UNION ALL
  SELECT 'GUROWNG_rows', COUNT(*), 'Distributed security user groups'
    FROM bansecr.gurowng
  UNION ALL
  SELECT 'GUROWNR_rows', COUNT(*), 'Distributed security object ownership'
    FROM bansecr.gurownr
  UNION ALL
  SELECT 'GURUSRI_rows', COUNT(*), 'VPD Institution/Banner user (MEP if >0)'
    FROM bansecr.gurusri
  UNION ALL
  SELECT 'GTVVPDI_rows', COUNT(*), 'VPD Institution codes'
    FROM bansecr.gtvvpdi
  UNION ALL
  SELECT 'GURALOG_total', COUNT(*), 'Security violation log total'
    FROM bansecr.guralog
  UNION ALL
  SELECT 'GURALOG_last30d', COUNT(*), 'Security violations last 30 days'
    FROM bansecr.guralog WHERE guralog_activity_date >= SYSDATE-30
  UNION ALL
  SELECT 'GURAEAC_rows', COUNT(*), 'Audit trail of GOBEACC changes'
    FROM bansecr.guraeac
  UNION ALL
  SELECT 'GURAUOB_rows', COUNT(*), 'Audit trail of GURUOBJ changes'
    FROM bansecr.gurauob
  UNION ALL
  SELECT 'GURLOGN_rows', COUNT(*), 'Oracle login log (GURUCLS-based)'
    FROM bansecr.gurlogn
  UNION ALL
  SELECT 'GURALGN_rows', COUNT(*), 'Login activity (GURUCLS)'
    FROM bansecr.guralgn
  UNION ALL
  SELECT 'GURAULG_rows', COUNT(*), 'Login activity (any Banner user)'
    FROM bansecr.guraulg
  UNION ALL
  SELECT 'GUVUACC_rows', COUNT(*), 'VIEW: Object Access By User'
    FROM bansecr.guvuacc
  UNION ALL
  SELECT 'GUVUOBJ_rows', COUNT(*), 'VIEW: who has what access to objects'
    FROM bansecr.guvuobj
  UNION ALL
  SELECT 'GUVDFTR_rows', COUNT(*), 'VIEW: users default roles'
    FROM bansecr.guvdftr
  UNION ALL
  SELECT 'GUVRPRV_rows', COUNT(*), 'VIEW: role privileges flat'
    FROM bansecr.guvrprv
  UNION ALL
  SELECT 'GUBIPRF_rows', COUNT(*), 'Site profile (should be 1)'
    FROM bansecr.gubiprf
  UNION ALL
  SELECT 'GUBROLE_rows', COUNT(*), 'Banner role password store'
    FROM bansecr.gubrole
  --  === distributions ===
  UNION ALL
  SELECT 'GURUOBJ_suffix_' || NVL(SUBSTR(guruobj_role,-1),'(null)'),
         COUNT(*), 'Role-suffix distribution (Q/M/B/U...)'
    FROM bansecr.guruobj
   GROUP BY SUBSTR(guruobj_role,-1)
  UNION ALL
  SELECT 'GURACLS_audit_' || guracls_audit_action,
         COUNT(*), 'audit_action dist; D=deleted'
    FROM bansecr.guracls
   GROUP BY guracls_audit_action
) ORDER BY metric;


-- ============================================================
-- PROBES -- run each separately; some may fail, that's fine.
-- Highlight one statement and press F5.
-- ============================================================

-- Probe 1: Is GOBEACC in BANSECR?
-- SELECT 'GOBEACC_in_bansecr' AS metric, COUNT(*) AS val FROM bansecr.gobeacc;

-- Probe 2: Is GOBEACC in GENERAL?
-- SELECT 'GOBEACC_in_general' AS metric, COUNT(*) AS val FROM general.gobeacc;

-- Probe 3: Is GOBEACC reachable by synonym (no schema)?
-- SELECT 'GOBEACC_public' AS metric, COUNT(*) AS val FROM gobeacc;

-- Probe 4: Where is GOBEACC actually owned? (shows real schema)
-- SELECT OWNER, TABLE_NAME FROM all_tables WHERE TABLE_NAME='GOBEACC';

-- Probe 5: Banner Oracle roles (may need DBA -- fallback below)
-- SELECT 'ORACLE_ROLE_'||ROLE AS metric, 1 AS val FROM dba_roles
--  WHERE ROLE LIKE 'BAN%' OR ROLE LIKE '%SECURITY%';
-- Fallback (always works -- shows roles of the CURRENT user):
-- SELECT 'MY_ROLE_'||GRANTED_ROLE AS metric, 1 AS val FROM user_role_privs;

-- Probe 6: FGAC check (catalog shows WCC doesn't have these, but confirm):
-- SELECT COUNT(*) FROM bansecr.gorfgac;   -- should error: ORA-00942

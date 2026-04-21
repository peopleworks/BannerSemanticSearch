-- ============================================================
-- BANNER SECURITY: Health-check / diagnostic (v2)
-- Output: security_health_check.txt  (METRIC|VALUE|NOTE)
--
-- Single-file output via PL/SQL with per-query exception handling.
-- If a table doesn't exist or lacks grants, that line reports
-- 'N/A|<error>' and the rest continue. No UNION needed.
--
-- Run against PROD_BRO (read-only). All SELECTs, no mutation.
-- ============================================================

SET SERVEROUTPUT ON SIZE UNLIMITED
SET LINESIZE 4000
SET FEEDBACK OFF
SET PAGESIZE 0
SET TRIMSPOOL ON
SET VERIFY OFF
SET ECHO OFF

SPOOL security_health_check.txt

DECLARE
  v_cnt NUMBER;

  PROCEDURE try(p_label VARCHAR2, p_note VARCHAR2, p_sql VARCHAR2) IS
  BEGIN
    EXECUTE IMMEDIATE p_sql INTO v_cnt;
    DBMS_OUTPUT.PUT_LINE(p_label || '|' || v_cnt || '|' || p_note);
  EXCEPTION
    WHEN OTHERS THEN
      DBMS_OUTPUT.PUT_LINE(p_label || '|N/A|' || SUBSTR(SQLERRM, 1, 180));
  END;
BEGIN
  DBMS_OUTPUT.PUT_LINE('METRIC|VALUE|NOTE');

  -- =======  CORE USER/CLASS TABLES  =======
  try('GURACLS_rows_active', 'User->class active (audit_action<>D)',
      'SELECT COUNT(*) FROM bansecr.guracls WHERE guracls_audit_action<>''D''');
  try('GURACLS_rows_total',  'User->class including deleted audit rows',
      'SELECT COUNT(*) FROM bansecr.guracls');
  try('GURUCLS_rows', 'Legacy user->class (pre-9; non-zero means legacy active)',
      'SELECT COUNT(*) FROM bansecr.gurucls');
  try('GTVCLAS_rows', 'Class-code validation table',
      'SELECT COUNT(*) FROM bansecr.gtvclas');
  try('GTVSGRP_rows', 'Security group validation',
      'SELECT COUNT(*) FROM bansecr.gtvsgrp');

  -- =======  OBJECT / ACCESS  =======
  try('GURUOBJ_rows', 'User->object direct grants (bypass class)',
      'SELECT COUNT(*) FROM bansecr.guruobj');
  try('GURAOBJ_rows', 'Object master + default role per object',
      'SELECT COUNT(*) FROM bansecr.guraobj');
  try('GUVUACC_rows', 'VIEW: Object Access By User (pre-joined)',
      'SELECT COUNT(*) FROM bansecr.guvuacc');
  try('GUVUOBJ_rows', 'VIEW: who has what access to objects',
      'SELECT COUNT(*) FROM bansecr.guvuobj');
  try('GUVDFTR_rows', 'VIEW: users default roles',
      'SELECT COUNT(*) FROM bansecr.guvdftr');

  -- =======  ACCOUNT / ENTERPRISE (GOBEACC lives outside BANSECR) =======
  try('GOBEACC_bansecr', 'Accounts table via bansecr (unlikely)',
      'SELECT COUNT(*) FROM bansecr.gobeacc');
  try('GOBEACC_general', 'Accounts table via general schema',
      'SELECT COUNT(*) FROM general.gobeacc');
  try('GOBEACC_direct',  'Accounts table without schema prefix (public synonym)',
      'SELECT COUNT(*) FROM gobeacc');

  -- =======  ROLES / CUSTOM ROLES  =======
  try('GURCROL_rows', 'Custom roles defined at WCC',
      'SELECT COUNT(*) FROM bansecr.gurcrol');
  try('GUVRPRV_rows', 'VIEW: role privileges flat',
      'SELECT COUNT(*) FROM bansecr.guvrprv');
  try('GUBROLE_rows', 'Banner role passwords (row per Oracle role)',
      'SELECT COUNT(*) FROM bansecr.gubrole');

  -- =======  SECURITY GROUPS / DISTRIBUTED SECURITY  =======
  try('GURBGRP_rows', 'Business profiles in security group',
      'SELECT COUNT(*) FROM bansecr.gurbgrp');
  try('GURCGRP_rows', 'Classes in security group',
      'SELECT COUNT(*) FROM bansecr.gurcgrp');
  try('GURUGRP_rows', 'Users in security group',
      'SELECT COUNT(*) FROM bansecr.gurugrp');
  try('GUROGRP_rows', 'Objects in security group',
      'SELECT COUNT(*) FROM bansecr.gurogrp');
  try('GUROWNG_rows', 'Distributed security user groups',
      'SELECT COUNT(*) FROM bansecr.gurowng');
  try('GUROWNR_rows', 'Distributed security object ownership',
      'SELECT COUNT(*) FROM bansecr.gurownr');

  -- =======  MEP / VPD  =======
  try('GURUSRI_rows', 'VPD Institution / Banner User (MEP enabled if >0)',
      'SELECT COUNT(*) FROM bansecr.gurusri');
  try('GTVVPDI_rows', 'VPD Institution code validation',
      'SELECT COUNT(*) FROM bansecr.gtvvpdi');

  -- =======  AUDIT / VIOLATION LOG  =======
  try('GURALOG_total', 'Security violation log total',
      'SELECT COUNT(*) FROM bansecr.guralog');
  try('GURALOG_last30d', 'Security violations last 30 days',
      'SELECT COUNT(*) FROM bansecr.guralog WHERE guralog_activity_date>=SYSDATE-30');
  try('GURAEAC_rows', 'Audit trail of GOBEACC changes',
      'SELECT COUNT(*) FROM bansecr.guraeac');
  try('GURAUOB_rows', 'Audit trail of GURUOBJ changes',
      'SELECT COUNT(*) FROM bansecr.gurauob');
  try('GURSQLL_rows', 'Dynamically-generated SQL log',
      'SELECT COUNT(*) FROM bansecr.gursqll');

  -- =======  LOGIN ACTIVITY  =======
  try('GURLOGN_rows', 'Login log (GURUCLS-based)',
      'SELECT COUNT(*) FROM bansecr.gurlogn');
  try('GURALGN_rows', 'Login-activity related to GURUCLS',
      'SELECT COUNT(*) FROM bansecr.guralgn');
  try('GURAULG_rows', 'Login-activity for Banner users (GURUCLS or GURUOBJ)',
      'SELECT COUNT(*) FROM bansecr.guraulg');

  -- =======  DISTRIBUTIONS  =======
  DECLARE
    CURSOR c_suffix IS
      SELECT SUBSTR(guruobj_role, -1) AS suffix, COUNT(*) AS n
        FROM bansecr.guruobj
       GROUP BY SUBSTR(guruobj_role, -1)
       ORDER BY 1;
  BEGIN
    FOR r IN c_suffix LOOP
      DBMS_OUTPUT.PUT_LINE('GURUOBJ_suffix_' || NVL(r.suffix,'(null)') || '|' ||
                           r.n || '|Role-suffix distribution (Q/M/B/U...)');
    END LOOP;
  EXCEPTION WHEN OTHERS THEN
    DBMS_OUTPUT.PUT_LINE('GURUOBJ_suffix_dist|N/A|' || SUBSTR(SQLERRM,1,180));
  END;

  DECLARE
    CURSOR c_audit IS
      SELECT guracls_audit_action AS act, COUNT(*) AS n
        FROM bansecr.guracls
       GROUP BY guracls_audit_action
       ORDER BY 1;
  BEGIN
    FOR r IN c_audit LOOP
      DBMS_OUTPUT.PUT_LINE('GURACLS_audit_' || r.act || '|' || r.n ||
                           '|D=deleted; must filter out in reports');
    END LOOP;
  EXCEPTION WHEN OTHERS THEN
    DBMS_OUTPUT.PUT_LINE('GURACLS_audit_dist|N/A|' || SUBSTR(SQLERRM,1,180));
  END;

  -- =======  ORACLE ROLES  =======
  DECLARE
    CURSOR c_role IS
      SELECT ROLE FROM dba_roles
       WHERE ROLE LIKE 'BAN%' OR ROLE LIKE '%SECURITY%'
       ORDER BY ROLE;
  BEGIN
    FOR r IN c_role LOOP
      DBMS_OUTPUT.PUT_LINE('ORACLE_ROLE_' || r.ROLE || '|1|Banner-related Oracle role present');
    END LOOP;
  EXCEPTION WHEN OTHERS THEN
    -- dba_roles often restricted; fall back to user_role_privs
    DBMS_OUTPUT.PUT_LINE('ORACLE_ROLE_dba_roles|N/A|' || SUBSTR(SQLERRM,1,180));
    BEGIN
      FOR r IN (SELECT GRANTED_ROLE FROM user_role_privs WHERE GRANTED_ROLE LIKE 'BAN%') LOOP
        DBMS_OUTPUT.PUT_LINE('MY_ROLE_' || r.GRANTED_ROLE || '|1|Current user has this Banner role');
      END LOOP;
    EXCEPTION WHEN OTHERS THEN
      DBMS_OUTPUT.PUT_LINE('MY_ROLE_user_role_privs|N/A|' || SUBSTR(SQLERRM,1,180));
    END;
  END;

  -- =======  GUBIPRF — institution profile (version, security level)  =======
  BEGIN
    FOR r IN (SELECT * FROM bansecr.gubiprf WHERE ROWNUM=1) LOOP
      DBMS_OUTPUT.PUT_LINE('GUBIPRF_present|1|Site profile row found (one row expected)');
    END LOOP;
  EXCEPTION WHEN OTHERS THEN
    DBMS_OUTPUT.PUT_LINE('GUBIPRF_present|N/A|' || SUBSTR(SQLERRM,1,180));
  END;

  -- =======  FGAC / VBS footprint (expected N/A at WCC based on catalog)  =======
  try('GORFGAC_rules', 'FGAC rules (N/A = VPD not installed at WCC)',
      'SELECT COUNT(*) FROM bansecr.gorfgac');
  try('GORFDPL_rows', 'FGAC predicates',
      'SELECT COUNT(*) FROM bansecr.gorfdpl');

  DBMS_OUTPUT.PUT_LINE('HEALTHCHECK_done|ok|end of diagnostic');
END;
/

SPOOL OFF

-- ============================================================
-- BANNER SECURITY SCHEMA: Foreign-key constraints
-- Output: bansecr_relationships.txt
--         CHILD_TABLE|CHILD_COLUMN|PARENT_TABLE|PARENT_COLUMN|CONSTRAINT_NAME
-- Run against PROD_BRO (read-only).
-- Captures FKs inside BANSECR and from BANSECR into SATURN/PAYROLL/etc.
-- ============================================================

SET LINESIZE 500
SET PAGESIZE 0
SET FEEDBACK OFF
SET HEADING OFF
SET TRIMSPOOL ON
SET VERIFY OFF
SET ECHO OFF

SPOOL bansecr_relationships.txt

SELECT cc.TABLE_NAME  || '|' ||
       cc.COLUMN_NAME || '|' ||
       rc.TABLE_NAME  || '|' ||
       rc.COLUMN_NAME || '|' ||
       c.CONSTRAINT_NAME
FROM   all_constraints  c
JOIN   all_cons_columns cc
       ON  cc.CONSTRAINT_NAME = c.CONSTRAINT_NAME
       AND cc.OWNER           = c.OWNER
JOIN   all_cons_columns rc
       ON  rc.CONSTRAINT_NAME = c.R_CONSTRAINT_NAME
       AND rc.OWNER           = c.R_OWNER
       AND rc.POSITION        = cc.POSITION
WHERE  c.CONSTRAINT_TYPE = 'R'
       AND c.OWNER = 'BANSECR'
ORDER BY cc.TABLE_NAME, cc.COLUMN_NAME;

SPOOL OFF

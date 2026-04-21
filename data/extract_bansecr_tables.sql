-- ============================================================
-- BANNER SECURITY SCHEMA: Table/View extraction
-- Output: bansecr_tables.txt  (TABLE_NAME|TYPE|DESCRIPTION)
-- Run against PROD_BRO (read-only). ~100-200 rows expected.
-- ============================================================

SET LINESIZE 2000
SET PAGESIZE 0
SET FEEDBACK OFF
SET HEADING OFF
SET TRIMSPOOL ON
SET LONG 4000
SET VERIFY OFF
SET ECHO OFF

SPOOL bansecr_tables.txt

SELECT trim(atc.TABLE_NAME) || '|' ||
       CASE WHEN ao.OBJECT_TYPE = 'TABLE' THEN 'TABLE' ELSE 'VIEW' END || '|' ||
       trim(NVL(atc.COMMENTS, '(no comments)'))
FROM   all_tab_comments atc
JOIN   all_objects ao
       ON  ao.OWNER       = atc.OWNER
       AND ao.OBJECT_NAME = atc.TABLE_NAME
       AND ao.OBJECT_TYPE IN ('TABLE', 'VIEW')
WHERE  atc.OWNER = 'BANSECR'
ORDER BY atc.TABLE_NAME;

SPOOL OFF

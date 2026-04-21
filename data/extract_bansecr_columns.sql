-- ============================================================
-- BANNER SECURITY SCHEMA: Column extraction
-- Output: bansecr_columns.txt  (TABLE_NAME|COLUMN_NAME|DESCRIPTION)
-- Run against PROD_BRO (read-only). ~2000-4000 rows expected.
-- ============================================================

SET LINESIZE 2000
SET PAGESIZE 0
SET FEEDBACK OFF
SET HEADING OFF
SET TRIMSPOOL ON
SET LONG 4000
SET VERIFY OFF
SET ECHO OFF

SPOOL bansecr_columns.txt

SELECT trim(c.TABLE_NAME) || '|' ||
       c.COLUMN_NAME || '|' ||
       trim(NVL(c.COMMENTS, '(no comments)'))
FROM   ALL_COL_COMMENTS c
WHERE  c.OWNER = 'BANSECR'
ORDER BY c.TABLE_NAME, c.COLUMN_NAME;

SPOOL OFF

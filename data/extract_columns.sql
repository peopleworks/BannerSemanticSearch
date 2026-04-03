-- ============================================================
-- Banner Schema Search - Extract Column Definitions
-- ============================================================
-- Output: field_info.txt
-- Format: TABLE_NAME|COLUMN_NAME|DESCRIPTION
--
-- SQL*Plus Usage:
--   SET LINESIZE 2000
--   SET PAGESIZE 0
--   SET FEEDBACK OFF
--   SET HEADING OFF
--   SET TRIMSPOOL ON
--   SET LONG 4000
--   SPOOL field_info.txt
--   @extract_columns.sql
--   SPOOL OFF
--
-- Note: This is the largest extraction (~130K rows, ~11 MB).
-- May take 10-30 seconds depending on your database.
-- Adjust the OWNER list to match your institution's schemas.
-- ============================================================

SELECT trim(c.TABLE_NAME) || '|' ||
       c.COLUMN_NAME || '|' ||
       trim(NVL(c.COMMENTS, '(no comments)'))
FROM   ALL_COL_COMMENTS c
WHERE  c.OWNER IN ('SATURN', 'PAYROLL', 'POSNCTL', 'BANINST1', 'GENERAL', 'FIMSMGR')
ORDER BY c.TABLE_NAME, c.COLUMN_NAME;

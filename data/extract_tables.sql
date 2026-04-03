-- ============================================================
-- Banner Schema Search - Extract Table Definitions
-- ============================================================
-- Output: table_info.txt
-- Format: TABLE_NAME|TYPE|DESCRIPTION
--
-- SQL*Plus Usage:
--   SET LINESIZE 2000
--   SET PAGESIZE 0
--   SET FEEDBACK OFF
--   SET HEADING OFF
--   SET TRIMSPOOL ON
--   SET LONG 4000
--   SPOOL table_info.txt
--   @extract_tables.sql
--   SPOOL OFF
--
-- Adjust the OWNER list to match your institution's schemas.
-- ============================================================

SELECT trim(TABLE_NAME) || '|' || TABLE_TYPE || '|' ||
       trim(NVL(COMMENTS, '(no comments)'))
FROM   all_tab_comments
WHERE  OWNER IN ('SATURN', 'PAYROLL', 'POSNCTL', 'BANINST1', 'GENERAL', 'FIMSMGR')
ORDER BY TABLE_NAME;

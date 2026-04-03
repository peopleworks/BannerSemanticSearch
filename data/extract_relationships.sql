-- ============================================================
-- Banner Schema Search - Extract Table Relationships
-- ============================================================
-- Run this in SQL*Plus or SQL Developer against your Banner Oracle instance.
-- Output: relationships.txt (pipe-delimited)
-- Format: CHILD_TABLE|CHILD_COLUMN|PARENT_TABLE|PARENT_COLUMN|CONSTRAINT_NAME
--
-- Usage:
--   SET LINESIZE 500
--   SET PAGESIZE 0
--   SET FEEDBACK OFF
--   SET HEADING OFF
--   SPOOL relationships.txt
--   @extract_relationships.sql
--   SPOOL OFF
-- ============================================================

SELECT
    cc.table_name || '|' ||
    cc.column_name || '|' ||
    rc.table_name || '|' ||
    rc.column_name || '|' ||
    c.constraint_name
FROM all_constraints c
JOIN all_cons_columns cc
    ON cc.constraint_name = c.constraint_name
    AND cc.owner = c.owner
JOIN all_cons_columns rc
    ON rc.constraint_name = c.r_constraint_name
    AND rc.owner = c.r_owner
    AND rc.position = cc.position
WHERE c.constraint_type = 'R'
    AND c.owner IN ('SATURN', 'PAYROLL', 'POSNCTL', 'BANINST1', 'GENERAL', 'FIMSMGR')
ORDER BY cc.table_name, cc.column_name;

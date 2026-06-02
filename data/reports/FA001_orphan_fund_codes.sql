-- REPORT_ID: FA001
-- TITLE: Orphan Fund Codes — Awards Hidden by INCLUDE-list Reports
-- CATEGORY: Financial Aid Audit
-- TABLES: RPRAWRD, RNVAND0
-- SEVERITY: MEDIUM
-- DESCRIPTION: For any Financial Aid report whose "OTHER" column uses a hardcoded IN-list of fund codes, this query enumerates every fund code actually awarded to the report's population and classifies each as either "in own column" (already a dedicated report column), "in OTHER today" (currently captured by the IN-list), or "*** MISSING FROM REPORT ***" (aid that exists but never shows on the report). Real-world impact at Waubonsee: applied to FAID1026 on aid year 2526, surfaced 149 orphan codes representing $1,361,345 in awards hidden from advisors — including federal Direct PLUS Loans and Alternative loans never shown anywhere on the report.
-- WHEN_TO_USE: Annual / per-aid-year audit of any FA report that uses fixed fund_code INCLUDE lists. Especially valuable when (a) the IN-list hasn't been touched in years and FA has created new scholarship codes since, (b) a Director of FA reports a discrepancy between "what we awarded" totals and "what advisors see on the report." Solution pattern when orphans are found: flip the OTHER column from an INCLUDE list to an EXCLUDE list — anything not already in a named column flows into OTHER automatically, future-proof for new fund codes.
-- CAVEATS: Customize three things below before running — POPULATION (the WHERE clause that defines the report's universe), OWN_COLUMN_CODES (fund codes that already have a dedicated column), and OTHER_INCLUDE_LIST (the report's current OTHER membership). RFRBASE join is omitted — if you have grants to RFRBASE, add `LEFT JOIN rfrbase fb ON fb.rfrbase_fund_code = ra.rprawrd_fund_code` to enrich each row with the fund description. Bind variable `:aid_year` is the Banner aid year code (e.g. '2526' for 2025-26). Read-only — no DML.

WITH report_population AS (
    -- ============================================================
    -- CUSTOMIZE #1 — POPULATION
    -- Replace with the WHERE clause your report uses to identify
    -- its student universe. Example below matches FAID1026 (Waubonsee):
    --   "RNVAND0 rows for the given aid year with budget > 0".
    -- ============================================================
    SELECT rnvand0_pidm AS pidm
      FROM rnvand0
     WHERE rnvand0_aidy_code     = :aid_year
       AND rnvand0_budget_amount > 0
),
classified AS (
    SELECT
        ra.rprawrd_fund_code  AS fund_code,
        ra.rprawrd_pidm,
        ra.rprawrd_offer_amt,
        CASE
            -- ============================================================
            -- CUSTOMIZE #2 — OWN_COLUMN_CODES
            -- Fund codes that already have a dedicated column on the
            -- report. List below matches FAID1026's 7 named columns.
            -- ============================================================
            WHEN ra.rprawrd_fund_code IN ('PELL','IIA','MAP','SEOG','FWS','DLSUB','DLUNSB')
                                                          THEN 'in own column'
            -- ============================================================
            -- CUSTOMIZE #3 — OTHER_INCLUDE_LIST
            -- The hardcoded list inside the report's current "OTHER"
            -- subquery. List below matches FAID1026's 10-code OTHER IN-list.
            -- ============================================================
            WHEN ra.rprawrd_fund_code IN ('ADMITS','ATHL','EMERG','EMPWAV','FDN','GUST','ING','IVG','PSCH','MIAPOW')
                                                          THEN 'in OTHER today'
            ELSE                                               '*** MISSING FROM REPORT ***'
        END                   AS report_status
      FROM rprawrd ra
     WHERE ra.rprawrd_aidy_code = :aid_year
       AND ra.rprawrd_pidm IN (SELECT pidm FROM report_population)
)
SELECT
    fund_code,
    report_status,
    COUNT(DISTINCT rprawrd_pidm)       AS student_count,
    SUM(rprawrd_offer_amt)             AS total_offered,
    ROUND(AVG(rprawrd_offer_amt), 2)   AS avg_offered,
    MIN(rprawrd_offer_amt)             AS min_offered,
    MAX(rprawrd_offer_amt)             AS max_offered
  FROM classified
 GROUP BY fund_code, report_status
 ORDER BY
    --  Orphan codes first (sorted by dollar impact), then known codes
    CASE WHEN report_status = '*** MISSING FROM REPORT ***' THEN 0 ELSE 1 END,
    total_offered DESC NULLS LAST
;

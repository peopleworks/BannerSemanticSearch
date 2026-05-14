"""
Headless smoke test: paste Michele Kellen's Argos report SQL into the SQL
Explainer and report the error/warning/pass counts + any column-not-found
errors that mention PWVEMPS / PERHOUR / NBBPOSN / NBRJOBS.

The goal is to confirm that after the recent parser fixes:
  - comma-separated FROM lists are recognized
  - Argos :main_* parameters surface as informational passes
  - PWVEMPS_* columns no longer flag as fantasms
"""
from __future__ import annotations
import sys
from pathlib import Path

#  Force UTF-8 stdout — Windows defaults to cp1252 which can't print emojis
#  from validator messages ("Copy fix" buttons, ellipsis, etc).
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not installed. pip install playwright && playwright install chromium")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / 'docs' / 'index.html'
URL = 'file:///' + str(HTML).replace('\\', '/')

ARGOS_SQL = """SELECT data.*,
       case when Auth_hours is null
            then Hours_Worked
            when (Hours_Worked - nvl(Auth_hours, 0)) < 0
            then 0
            else (Hours_Worked - nvl(Auth_hours, 0))
       end as over,
       case when Auth_hours is null
            then 0
            when (Hours_Worked - nvl(Auth_hours, 0)) < 0
            then (Hours_Worked - nvl(Auth_hours, 0))
            else 0
       end as under,
       case when :main_CB_allecls = 0 then
          (SELECT listagg(EClass,', ') WITHIN GROUP(
           ORDER BY
           EClass
            ) as EClass
           from
          (SELECT regexp_substr('01,02,03,04,05,06,07,08,09,10,11,12,16', '[^,]+', 1, level) as EClass
            FROM dual
              CONNECT BY level <= regexp_count('01,02,03,04,05,06,07,08,09,10,11,12,16', ',') + 1)
            where EClass = :main_MC_ecls.Code )
         else 'All'
         end as join_ecls, :main_CB_allecls as allecls
FROM
(
SELECT * FROM
(
    SELECT PWVEMPS_FULL_NAME AS Full_Name, SUM(PERHOUR_HRS) AS Hours_Worked,
                 DECODE(PWVEMPS_JOB_ECLS_CODE,'04','40.0','06','40.0',
        (SELECT NBRJOBS_CONTRACT_NO
                        FROM NBRJOBS zzz WHERE
                               NBRJOBS_PIDM = PWVEMPS_PIDM AND
                                   NBRJOBS_POSN = PWVEMPS_job_POSN AND
                                   NBRJOBS_SUFF = PWVEMPS_job_SUFF AND
                                   NBRJOBS_STATUS <> 'T' AND
                                   NBRJOBS_EFFECTIVE_DATE = ( SELECT MAX(NBRJOBS_EFFECTIVE_DATE)
                                                                                          FROM NBRJOBS yyy WHERE
                                                               yyy.NBRJOBS_PIDM = zzz.NBRJOBS_PIDM AND
                                                                                                   yyy.NBRJOBS_POSN = zzz.NBRJOBS_POSN AND
                                                                                                   yyy.NBRJOBS_SUFF = zzz.NBRJOBS_SUFF AND
                                                                                                   yyy.NBRJOBS_STATUS <> 'T' AND
                                                                                                   yyy.NBRJOBS_EFFECTIVE_DATE <=
                                                                                                          (TRUNC(:main_EB_week_of,'DAY')+6)
                                      ))
    ) AS Auth_hours,
 PWVEMPS_JOB_POSN AS Position,
 PWVEMPS_JOB_SUFF AS Suffix,
 PWVEMPS_JOB_TITLE AS Title,
  (TRUNC(:main_EB_week_of, 'DAY')) AS StartDay,
  (TRUNC(:main_EB_week_of, 'DAY')+6) AS EndDay,
  pwvemps_job_timesheet_orgn as Orgn,
PWVEMPS_ECLS_CODE as ECLS_Code,
  nbbposn_type as PType
 FROM PERHOUR, PERJOBH aa, PWVEMPS, nbbposn WHERE
        PERHOUR_JOBS_SEQNO = PERJOBH_SEQNO
        AND PERJOBH_TETH_SEQNO =
            (SELECT MAX(PERJOBH_TETH_SEQNO) FROM PERJOBH bb
             WHERE aa.PERJOBH_SEQNO = bb.PERJOBH_SEQNO)
        AND PERHOUR_TIME_ENTRY_DATE BETWEEN
                (TRUNC(:main_EB_week_of, 'DAY')) AND
                (TRUNC(:main_EB_week_of, 'DAY')+6)
                           and perjobh_action_ind <> 'R'
        AND PWVEMPS_PIDM = PERJOBH_PIDM
        AND PWVEMPS_JOB_POSN = PERJOBH_POSN
   and pwvemps_job_posn = nbbposn_posn
   and nbbposn_status = 'A'
        AND PWVEMPS_JOB_SUFF = PERJOBH_SUFF
    GROUP BY
        PWVEMPS_PIDM, PWVEMPS_FULL_NAME, PWVEMPS_JOB_ECLS_CODE, PWVEMPS_JOB_AUTHORIZED_HOURS, PWVEMPS_JOB_POSN, PWVEMPS_JOB_SUFF, PWVEMPS_JOB_TITLE, PWVEMPS_ECLS_CODE,pwvemps_job_timesheet_orgn, nbbposn_type
)
WHERE
          (:main_DD_display_over_hours    = 'A' or
           :main_DD_display_over_hours = case   when  Hours_Worked > nvl(Auth_Hours,0)
                                               then  'O'
                                               when  Hours_Worked < nvl(Auth_Hours,99)
                                               then  'U'
                                               else 'A'
                                               end)
           and ( ECLS_Code = :main_MC_ecls or :main_CB_allecls = 1)
) data
ORDER BY FULL_NAME
"""


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={'width': 1600, 'height': 900})
        page = ctx.new_page()
        page.goto(URL + '#/sql', wait_until='domcontentloaded')
        page.wait_for_selector('#sqlInput', timeout=8000)
        page.locator('#sqlInput').fill(ARGOS_SQL)
        page.locator('#sqlExplainBtn').click()
        page.wait_for_selector('.sql-val-section', timeout=8000)

        # Count badges + extract each validation message
        errors = page.locator('.sql-val-item.error .sql-val-msg').all_inner_texts()
        warnings = page.locator('.sql-val-item.warning .sql-val-msg').all_inner_texts()
        passes = page.locator('.sql-val-item.pass .sql-val-msg').all_inner_texts()

        print('=== ERRORS (%d) ===' % len(errors))
        for e in errors:
            print('  -', e.replace('\n', ' | '))
        print()
        print('=== WARNINGS (%d) ===' % len(warnings))
        for w in warnings:
            print('  -', w.replace('\n', ' | '))
        print()
        print('=== PASSES (%d) ===' % len(passes))
        for p in passes:
            print('  -', p.replace('\n', ' | '))

        # Specifically check the regression we fixed
        bad_pwvemps = [e for e in errors if 'PWVEMPS_' in e]
        if bad_pwvemps:
            print()
            print('!! REGRESSION: %d errors still mention PWVEMPS_* columns:' % len(bad_pwvemps))
            for b in bad_pwvemps:
                print('   *', b.replace('\n', ' | '))
            return 1

        # Argos pass should be present
        argos_pass = [p for p in passes if 'Argos parameter' in p]
        if not argos_pass:
            print()
            print('!! REGRESSION: no "Argos parameter(s) detected" pass message.')
            return 1

        print()
        print('OK — no PWVEMPS_* fantasms, Argos params recognized.')
        return 0


if __name__ == '__main__':
    sys.exit(run())

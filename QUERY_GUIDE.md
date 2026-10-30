# Wellness Tracker query guide

The SQL reports are saved in `queries.py`. Use this guide to find a report in a
future session; the files preserve the code independently of chat history.

## Run a report

Run from the Wellness Tracker project directory:

```python
import importlib
import queries
from postgres import run_select

importlib.reload(queries)  # Pick up changes in an already-open notebook.
run_select(queries.weekly_stress_summary)
```

`postgres.run_select` returns a pandas DataFrame by default. Its connection
defaults to `LIVE_wellness_tracker`. It returns an empty DataFrame on error, so
check its printed error message when a report unexpectedly appears empty.
Configuration and credentials are loaded by `postgres.py` from `config.json`.
For database exploration, use SELECT statements; database initialization and
reset functions are unrelated to running reports.

Schema definitions: `sql/Create_tables.sql`. Stress dropdown labels:
`ui_functions.py`, in `ui_insert_stress`. Shared report CTEs: `_STRESS_CTES` in
`queries.py`; they are assembled into SQL strings, not database views or tables.

## Stress and activity reports

| Query name | What it answers |
| --- | --- |
| `stress_trends` | How is each stress source changing? Shows daily labels, scores, seven-calendar-day averages, and scored-day counts. |
| `weekly_stress_summary` | Which sources were most stressful each week? Includes high-stress days, scoring coverage, and change from the preceding calendar week. |
| `weekly_activity_breakdown` | Where did recorded activity time go each week? Ranks activities and shows their share of recorded minutes, days logged, and missing durations. |
| `activity_stress_comparison` | Is each activity associated with different stress on the same day or the next calendar day? Shows each stress source, comparison counts, average differences, and small-group labels. |
| `sleep_stress_productivity` | How do stress and productivity differ across recorded sleep durations? Groups sleep into four duration bands and shows contributing-day counts. |
| `stress_productivity_patterns` | Which productivity labels occur at each work-stress level? Shows counts and percentages within each stress level. |

## Interpret the results

- Stress scores follow the existing dropdown order: Completely Stress-Free = 0,
  Very Low Stress = 1, Slightly Stressed = 2, Moderately Stressed = 3, Highly
  Stressed = 4, Very Stressed = 5, Extremely Stressed = 6. An average is a
  descriptive summary of ordered labels, not a clinical measurement. High stress
  means a score of 4 or higher.
- No Work, missing values, and unknown stress labels are excluded from score
  averages. Weekly summaries expose excluded-day counts. Zero means a recorded
  Completely Stress-Free rating, not a missing entry.
- Weeks begin Monday. All reports use all available history. Current or partly
  logged weeks can have fewer observations; compare their counts as well as
  their averages. A week-to-week difference is NULL if the immediately preceding
  calendar week has no scored observations.
- Activity comparisons use only baseline dates with at least one activity log.
  An activity not logged on such a date might still have occurred. Multiple
  entries for an activity on one date count as one comparison day. Each activity
  is evaluated separately; activities can overlap on the same day. A next-day
  match uses the exact next calendar date, never the next available record.
- In activity comparisons, a negative score_difference means lower average
  stress on dates associated with the activity being logged. These comparisons
  do not establish cause and effect or adjust for work schedules, other
  activities, or other differences between days. Five days per group is only a
  display threshold for sample size, not a significance test.
- The sleep report uses actual wake dates in America/Indiana/Indianapolis time,
  subtracts recorded interruption minutes, and chooses the longest complete
  session per wake date. It excludes sessions with nonpositive elapsed duration
  or negative calculated sleep. It does not add shorter sessions or naps to that
  duration. Sleep bands are descriptive ranges, not personalized targets.
- Highly productive means Highly Productive or Exceptionally Productive.
  Productivity percentages exclude No Work, missing values, and unknown labels.

## Verification

On October 29, 2026, all six reports were executed successfully using a read-only
database transaction. The database contained 49 stress entries and 132 activity
entries at that time. No database records were changed.

Additional SELECT-only fixture checks covered calendar gaps, No Work and unknown
labels, repeated activity entries, missing durations, exact next-day matching,
wake-date alignment, multiple sleep sessions, and empty comparison groups.

# Wellness Tracker query guide

The SQL reports are saved in `queries.py`. Use this guide to find a report in a
future session; the files preserve the code independently of chat history.

## Run a report

Run from the Wellness Tracker project directory:

```python
import importlib
import queries
import postgres

importlib.reload(queries)  # Pick up changes in an already-open notebook.
importlib.reload(postgres)
postgres.display_query(queries.weekly_stress_summary)
```

`postgres.display_query` shows all result rows and columns in a formatted HTML
table with horizontal and vertical scrolling, a 600-pixel maximum height, and
sticky column headers. It returns `None` by default, so the notebook shows only
the formatted table. It also accepts `to_csv_path` and `show_errors` and reuses
`run_select` for database access.

To display the table and keep the DataFrame for further work, explicitly request
it and assign the result:

```python
df = postgres.display_query(queries.weekly_stress_summary, return_df=True)
```

`display_query` always gets a DataFrame from `run_select` internally. Its own
`return_df` option controls whether that DataFrame is returned to the notebook.
After reloading `postgres`, re-run any `from postgres import display_query`
statement to refresh that imported function too.

Use `postgres.run_select` for application code and dropdown data. It has no
display option or HTML rendering; `return_df=False` still returns `(rows, columns)`.
Replace earlier notebook examples of `run_select(..., display=True)` with
`display_query(...)`.

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

## Correlation reports

Reload `queries` after editing it, then run a report with the display helper:

```python
importlib.reload(queries)
postgres.display_query(queries.next_day_correlations)
```

| Query name | What it answers |
| --- | --- |
| `daily_wellness_factors` | Shows the daily nutrition, exercise, activity, sleep, and stress values used by the reports, plus entry counts and missing-data diagnostics. |
| `wellness_correlations` | Which measurements move together on the same date across food, exercise, activity, sleep, and stress? Includes both Pearson and Spearman coefficients. |
| `next_day_correlations` | How are today's measurements associated with sleep or stress on the exact next calendar day? |
| `activity_wellness_correlations` | How do minutes spent on individual activities relate to food, exercise, sleep, and stress on the same or next date? Includes activities logged on at least three distinct dates. |
| `food_exercise_recovery` | How do next-day sleep, stress, and activity differ when grouping days by calories and exercise together? Splits each variable at its median among days with both measurements. Also shows same-day activity. |

### Correlation definitions and data handling

- `pearson_r` measures linear association; `spearman_rho` measures association
  between ranks and is especially useful for ordered stress labels. Both range
  from -1 to +1: positive means the values tend to rise together; negative means
  one tends to decrease as the other increases. A value near zero does not rule
  out a relationship that these coefficients do not capture. Tied values receive
  average ranks, calculated separately for each pair's complete observations.
- Each coefficient uses only dates where both values exist. Check `paired_days`
  and the first/last factor dates. Pairs without any complete observations are
  absent; coefficients are NULL for fewer than three paired days or a constant
  value. The under-10, 10-29, and 30-or-more labels describe counts, not statistical
  significance or reliability guarantees. Larger eligible samples appear before
  tiny samples when ordering by the absolute Spearman coefficient.
- Same-day predictor/outcome columns identify the pair and do not establish a
  time order. For same-day pairs, sleep ended on that date and can precede the
  day's meals and exercise. Next-day reports match the factor date plus exactly
  one day to the outcome's date; they do not skip gaps. Sleep uses its actual
  wake date in Indianapolis time and the longest valid session, as described
  below. Unknown interruption totals are treated as zero, matching the existing
  sleep reports.
- Nutrition uses recorded quantities and combo component portions. Each source
  log is aggregated independently to avoid multiplying rows when joining meals,
  exercises, and activities. Combo matching includes both food ID and combo name.
  Repeated combo ingredients are handled without multiplying their contribution
  by the number of matching recipe rows. Missing combo definitions or portions
  make that day's nutrition values NULL; see `unresolved_food_entries`.
- Nutrition is based on current food and recipe definitions. The schema has no
  historical nutrient/recipe snapshots, so editing definitions can change past
  calculated totals. Logged food does not guarantee that every meal was entered.
  Dinner + snack calorie share is a meal-label measure; the schema has no actual
  meal timestamps to establish how late those foods were eaten.
- A day without exercise or activity entries has NULL minutes, not zero. A day's
  total is also NULL if any of its recorded durations are missing. Consequently,
  exercise correlations describe days with recorded exercise and complete
  durations, not exercise versus confirmed rest days. Cardio or strength can be
  zero on days when other exercise types were recorded. Named-activity reports
  use complete recorded durations only on dates that activity was logged; they
  do not fill unlogged days with zero minutes.
- `food_exercise_recovery` uses days with valid calorie and exercise totals for
  its cutpoints and groups. Its median values are descriptive, not recommended
  intake or exercise targets. Each outcome has a separate contributing-day
  count; a missing next-day result does not remove the baseline day from its group.
- These are exploratory associations, not causal or multivariable adjusted
  estimates. Diet, exercise, activities, work schedules, and time trends can
  overlap. Examining many pairs can produce large coefficients by chance;
  individual correlations and the combined grouping report do not isolate an
  independent effect of any one factor.

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

from datetime import date as Date


# food logged with food data and calorie totals
all_food_data = """
                
    SELECT 
        l.log_date,
        l.meal_type,
        f.name AS food,
        ROUND(f.carbohydrates, 1) AS carbs,
        ROUND(f.fiber, 1) AS fiber,
        ROUND(f.carbohydrates - f.fiber, 1) AS net_carbs,
        ROUND(f.proteins, 1) AS proteins,
        ROUND(f.fats, 1) AS fats,
        ROUND(f.calories, 1) AS cal_per_unit,
        ROUND(l.quantity, 1) AS quantity,
        l.combo_name,
        CASE WHEN l.combo_name is not null
		then
        ROUND(ac.serving_size, 1) 
		else null end AS qty_in_combo,

        CASE
            WHEN l.combo_name IS NOT NULL 
                THEN ROUND(f.calories * l.quantity * ac.serving_size, 1)
            ELSE ROUND(f.calories * l.quantity, 1)
        END AS total_calories, notes

    FROM food_log l

    LEFT JOIN food f
        ON f.food_id = l.food_id

    LEFT JOIN all_combos ac
        ON f.food_id = ac.food_id

    WHERE l.meal_type LIKE ANY (ARRAY['B%', 'L%', 'D%', 'S%'])

    ORDER BY
        l.log_date DESC,
        CASE
            WHEN l.meal_type LIKE 'B%' THEN 1
            WHEN l.meal_type LIKE 'L%' THEN 2
            WHEN l.meal_type LIKE 'D%' THEN 3
            WHEN l.meal_type LIKE 'S%' THEN 4
        END,
        l.combo_name
                """
                
                
# aggregated calories per meal.  should be a function to take a day, period or specifc time
def food_one_day(date):
    food = f"""
            SELECT  '{date}' AS log_date,
                    l.meal_type,
                    Round(SUM(
                        f.carbohydrates * l.quantity *
                        CASE
                            WHEN l.combo_name IS NOT NULL THEN ac.serving_size
                            ELSE 1
                        END
                    ), 1) AS carbs,
            
                    Round(SUM(
                        f.proteins * l.quantity *
                        CASE
                            WHEN l.combo_name IS NOT NULL THEN ac.serving_size
                            ELSE 1
                        END
                    ), 1) AS proteins,
            
                    Round(SUM(
                        f.fats * l.quantity *
                        CASE
                            WHEN l.combo_name IS NOT NULL THEN ac.serving_size
                            ELSE 1
                        END
                    ), 1) AS fats,
            
                    Round(SUM(
                        f.fiber * l.quantity *
                        CASE
                            WHEN l.combo_name IS NOT NULL THEN ac.serving_size
                            ELSE 1
                        END
                    ), 1) AS fiber,
            
                    Round(SUM(
                        f.calories * l.quantity *
                        CASE
                            WHEN l.combo_name IS NOT NULL THEN ac.serving_size
                            ELSE 1
                        END
                    ), 1) AS calories
            
                FROM food_log l
                LEFT JOIN food f
                    ON f.food_id = l.food_id
                LEFT JOIN all_combos ac
                    ON f.food_id = ac.food_id
                where l.log_date = DATE '{date}'
                GROUP BY l.meal_type
                ORDER BY l.meal_type;             
            """
    return food


total_calories_by_day = """
    SELECT
    l.log_date,
    ROUND(SUM(
        f.calories * l.quantity *
        CASE
            WHEN l.combo_name IS NOT NULL THEN ac.serving_size
            ELSE 1
        END
    ), 1) AS total_calories
FROM food_log l
LEFT JOIN food f
    ON f.food_id = l.food_id
LEFT JOIN all_combos ac
    ON f.food_id = ac.food_id
GROUP BY l.log_date
ORDER BY l.log_date DESC
                      """


def full_day_summary(log_date):
    """Return food, exercise, and activity rows for one date."""
    log_date = Date.fromisoformat(str(log_date)).isoformat()
    return f"""
WITH params AS (
    SELECT DATE '{log_date}' AS log_date
),
food AS (
    SELECT
        'food'::text AS section,
        f.name,
        l.quantity AS qty_or_duration,
        CASE
            WHEN l.combo_name IS NOT NULL
                THEN ROUND(f.calories * l.quantity * ac.serving_size, 1)
            ELSE ROUND(f.calories * l.quantity, 1)
        END AS total_calories,
        CONCAT(
            'Qty: ', l.quantity,
            ' | ',
            ROUND(
                CASE
                    WHEN l.combo_name IS NOT NULL
                        THEN f.calories * l.quantity * ac.serving_size
                    ELSE f.calories * l.quantity
                END,
                1
            ),
            ' cal'
        ) AS qty_duration,
        jsonb_build_object(
            'meal_type', l.meal_type,
            'notes', l.notes,
            'fiber', f.fiber,
            'carbs', f.carbohydrates,
            'fats', f.fats,
            'prtn', f.proteins,
            'combo_name', l.combo_name,
            'combo_component_servings', ac.serving_size
        ) AS details
    FROM food_log l
    JOIN params p
        ON p.log_date = l.log_date
    LEFT JOIN food f
        ON f.food_id = l.food_id
    LEFT JOIN all_combos ac
        ON ac.food_id = l.food_id
       AND l.combo_name = SUBSTRING(ac.combo_name FROM 2)
    WHERE l.meal_type IN ('Breakfast', 'Lunch', 'Dinner', 'Snack')
),
all_food AS (
    SELECT section, name, qty_duration AS measure, details
    FROM food
    UNION ALL
    SELECT
        'FOOD TOTAL'::text AS section,
        '' AS name,
        ROUND(SUM(total_calories), 1)::text || ' cal' AS measure,
        NULL::jsonb AS details
    FROM food
    HAVING COUNT(*) > 0
),
exercise AS (
    SELECT
        'exercise'::text AS section,
        CONCAT(e.exercise_type, ' | ', e.name) AS name,
        l.duration_minutes AS qty_or_duration,
        jsonb_build_object(
            'notes', l.notes
        ) AS details
    FROM exercise_log l
    JOIN params p
        ON p.log_date = l.log_date
    LEFT JOIN exercise e
        ON e.exercise_id = l.exercise_id
),
all_exercise AS (
    SELECT
        section,
        name,
        qty_or_duration::text AS measure,
        details
    FROM exercise
    UNION ALL
    SELECT
        'EXERCISE TOTAL'::text AS section,
        ''AS name,
        COALESCE(SUM(qty_or_duration), 0)::text || ' minutes' AS measure,
        NULL::jsonb AS details
    FROM exercise
),
activity AS (
    SELECT
        'activity'::text AS section,
        a.name,
        l.duration_minutes AS qty_or_duration,
        jsonb_build_object(
            'notes', l.notes
        ) AS details
    FROM activity_log l
    JOIN params p
        ON p.log_date = l.log_date
    LEFT JOIN activity a
        ON a.activity_id = l.activity_id
),
all_activity AS (
    SELECT
        section,
        name,
        qty_or_duration::text AS measure,
        details
    FROM activity
    UNION ALL
    SELECT
        'ACTIVITY TOTAL'::text AS section,
        '' AS name,
        COALESCE(SUM(qty_or_duration), 0)::text || ' minutes' AS measure,
        NULL::jsonb AS details
    FROM activity
),
stress AS (
    SELECT
        'Stress / Productivity'::text AS section,
        metric.name,
        metric.value AS measure,
        jsonb_build_object('notes', s.notes) AS details
    FROM stress_log s
    JOIN params p
        ON p.log_date = s.log_date
    CROSS JOIN LATERAL (
        VALUES
            ('Work productivity', s.work_productivity_level),
            ('Work stress', s.work_stress_level),
            ('Family stress', s.family_stress_level),
            ('Health stress', s.health_stress_level),
            ('Other stress', s.other_stress_level)
    ) AS metric(name, value)
    WHERE metric.value IS NOT NULL
),
sleep_nights AS (
    SELECT
        'Night before'::text AS name,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM sleep_log l
                JOIN params p ON l.log_date = p.log_date - 1
                WHERE EXTRACT(HOUR FROM l.bedtime) >= 20
            )
                THEN p.log_date - 1
            ELSE p.log_date
        END AS night_date
    FROM params p

    UNION ALL

    SELECT
        'Night after'::text AS name,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM sleep_log l
                JOIN params p ON l.log_date = p.log_date
                WHERE EXTRACT(HOUR FROM l.bedtime) >= 20
            )
                THEN p.log_date
            ELSE p.log_date + 1
        END AS night_date
    FROM params p
),
ranked_sleep AS (
    SELECT
        n.name,
        l.log_date,
        l.bedtime,
        l.wake_time,
        l.interruptions,
        l.total_interruption_minutes,
        l.notes,
        ROUND(
            EXTRACT(EPOCH FROM (l.wake_time - l.bedtime)) / 60
            - COALESCE(l.total_interruption_minutes, 0)
        )::int AS total_minutes,
        ROW_NUMBER() OVER (
            PARTITION BY n.name
            ORDER BY
                CASE
                    WHEN EXTRACT(HOUR FROM l.bedtime) >= 20 THEN 1
                    ELSE 2
                END,
                l.bedtime DESC
        ) AS row_num
    FROM sleep_nights n
    JOIN sleep_log l
        ON l.log_date = n.night_date
),
sleep AS (
    SELECT
        'sleep'::text AS section,
        name,
        (total_minutes / 60)::text || ' hrs ' ||
            (total_minutes % 60)::text || ' min' AS measure,
        jsonb_build_object(
            'log_date', log_date,
            'bedtime', bedtime,
            'wake_time', wake_time,
            'interruptions', interruptions,
            'total_interruption_minutes', total_interruption_minutes,
            'notes', notes
        ) AS details
    FROM ranked_sleep
    WHERE row_num = 1
),

summary_rows AS (
    SELECT section, name, measure, details
    FROM all_food
    UNION ALL
    SELECT section, name, measure, details
    FROM all_exercise
    UNION ALL
    SELECT section, name, measure, details
    FROM all_activity
    UNION ALL
    SELECT section, name, measure, details
    FROM stress
    UNION ALL
    SELECT section, name, measure, details
    FROM sleep
)

SELECT section, name, measure, details
FROM summary_rows
ORDER BY
    LOWER(REGEXP_REPLACE(section, ' TOTAL$', '')),
    section LIKE '% TOTAL',
    CASE WHEN section = 'sleep' AND name = 'Night after' THEN 1 ELSE 0 END,
    name;
"""


# Weekly exercise minutes and logging completeness by exercise type.
weekly_exercise = """
SELECT
    DATE_TRUNC('week', l.log_date)::date AS week_start,
    e.exercise_type,
    COUNT(DISTINCT l.log_date) AS days_exercised,
    COUNT(*) AS exercise_entries,
    SUM(l.duration_minutes) AS total_minutes,
    COUNT(*) FILTER (
        WHERE l.duration_minutes IS NULL
    ) AS entries_missing_duration
FROM exercise_log l
JOIN exercise e
    ON e.exercise_id = l.exercise_id
GROUP BY
    DATE_TRUNC('week', l.log_date)::date,
    e.exercise_type
ORDER BY week_start DESC, e.exercise_type;
"""


# Completed sleep sessions, including naps, with interruptions subtracted.
sleep_history = """
WITH sleep_minutes AS (
    SELECT
        sleep_log_id,
        log_date,
        bedtime,
        wake_time,
        interruptions,
        total_interruption_minutes,
        EXTRACT(EPOCH FROM (wake_time - bedtime)) / 60
            AS minutes_in_bed,
        notes
    FROM sleep_log
    WHERE bedtime IS NOT NULL
      AND wake_time IS NOT NULL
)
SELECT
    log_date,
    TO_CHAR(bedtime, 'HH12:MI AM') AS bedtime,
    TO_CHAR(wake_time, 'HH12:MI AM') AS wake_time,
    ROUND(minutes_in_bed / 60, 2) AS hrs_in_bed,
    interruptions,
    total_interruption_minutes inerruption_min,
    ROUND(
        (minutes_in_bed
            - COALESCE(total_interruption_minutes, 0)) / 60,
        2
    ) AS sleep_hrs,

    notes
FROM sleep_minutes
ORDER BY sleep_minutes.bedtime DESC, sleep_log_id DESC;
"""


# Water averages use recorded days; missing days are not counted as zero.
weekly_water = """
SELECT
    DATE_TRUNC('week', log_date)::date AS week_start,
    COUNT(*) AS days_logged,
    ROUND(AVG(total_oz), 1) AS average_oz_on_logged_days,
    MIN(total_oz) AS lowest_logged_oz,
    MAX(total_oz) AS highest_logged_oz,
    SUM(total_oz) AS total_logged_oz
FROM water_log
GROUP BY DATE_TRUNC('week', log_date)::date
ORDER BY week_start DESC;
"""


# Shared SELECT-only CTEs for stress reports. Scores follow the dropdown order:
# 0 = Completely Stress-Free, 6 = Extremely Stressed. They are ordinal summaries,
# not a clinical scale. No Work, NULL, and unrecognized labels have NULL scores.
_STRESS_CTES = """
stress_scale(label, score) AS (
    VALUES
        ('Completely Stress-Free', 0),
        ('Very Low Stress', 1),
        ('Slightly Stressed', 2),
        ('Moderately Stressed', 3),
        ('Highly Stressed', 4),
        ('Very Stressed', 5),
        ('Extremely Stressed', 6)
),
stress_observations AS (
    SELECT s.log_date, v.category, v.label, scale.score
    FROM stress_log s
    CROSS JOIN LATERAL (
        VALUES
            ('Work', s.work_stress_level),
            ('Family', s.family_stress_level),
            ('Health', s.health_stress_level),
            ('Other', s.other_stress_level)
    ) AS v(category, label)
    LEFT JOIN stress_scale scale ON scale.label = v.label
),
stress_daily AS (
    SELECT
        log_date,
        MAX(score) FILTER (WHERE category = 'Work') AS work_score,
        MAX(score) FILTER (WHERE category = 'Family') AS family_score,
        MAX(score) FILTER (WHERE category = 'Health') AS health_score,
        MAX(score) FILTER (WHERE category = 'Other') AS other_score
    FROM stress_observations
    GROUP BY log_date
)
"""


# Seven calendar days, including the current row's date; missing days are omitted
# from the average and exposed through scored_days_7d rather than filled with 0.
stress_trends = "WITH " + _STRESS_CTES + """
SELECT
    log_date,
    category,
    label AS stress_level,
    score AS stress_score,
    ROUND(AVG(score) OVER trailing_week, 2) AS average_score_7d,
    COUNT(score) OVER trailing_week AS scored_days_7d
FROM stress_observations
WINDOW trailing_week AS (
    PARTITION BY category
    ORDER BY log_date::timestamp
    RANGE BETWEEN INTERVAL '6 days' PRECEDING AND CURRENT ROW
)
ORDER BY log_date DESC, category;
"""


# Weekly stress sources, high-stress frequency (score >= 4), and change from the
# immediately preceding calendar week. Partial weeks show their actual counts.
weekly_stress_summary = "WITH " + _STRESS_CTES + """,
weekly AS (
    SELECT
        DATE_TRUNC('week', log_date)::date AS week_start,
        category,
        COUNT(*) AS days_logged,
        COUNT(score) AS days_scored,
        COUNT(*) FILTER (WHERE label = 'No Work') AS no_work_days,
        COUNT(*) FILTER (
            WHERE score IS NULL AND label IS DISTINCT FROM 'No Work'
        ) AS missing_or_unrecognized_days,
        AVG(score) AS average_score,
        COUNT(*) FILTER (WHERE score >= 4) AS high_stress_days
    FROM stress_observations
    GROUP BY DATE_TRUNC('week', log_date)::date, category
)
SELECT
    w.week_start,
    w.category,
    w.days_logged,
    w.days_scored,
    w.no_work_days,
    w.missing_or_unrecognized_days,
    ROUND(w.average_score, 2) AS average_score,
    w.high_stress_days,
    ROUND(
        100.0 * w.high_stress_days / NULLIF(w.days_scored, 0), 1
    ) AS high_stress_pct,
    ROUND(w.average_score - previous.average_score, 2)
        AS score_change_from_previous_week
FROM weekly w
LEFT JOIN weekly previous
    ON previous.category = w.category
   AND previous.week_start = w.week_start - 7
ORDER BY w.week_start DESC, w.average_score DESC NULLS LAST, w.category;
"""


# Ranked activity time within each week. Shares refer to recorded activity
# minutes; missing durations and days without logging are not estimated.
weekly_activity_breakdown = """
WITH weekly AS (
    SELECT
        DATE_TRUNC('week', l.log_date)::date AS week_start,
        a.activity_id,
        a.name AS activity,
        COUNT(*) AS entries,
        COUNT(DISTINCT l.log_date) AS days_logged,
        SUM(l.duration_minutes) AS recorded_minutes,
        COUNT(*) FILTER (
            WHERE l.duration_minutes IS NULL
        ) AS entries_missing_duration
    FROM activity_log l
    JOIN activity a USING (activity_id)
    GROUP BY DATE_TRUNC('week', l.log_date)::date, a.activity_id, a.name
)
SELECT
    week_start,
    activity,
    entries,
    days_logged,
    recorded_minutes,
    entries_missing_duration,
    DENSE_RANK() OVER (
        PARTITION BY week_start
        ORDER BY recorded_minutes DESC NULLS LAST
    ) AS time_rank,
    ROUND(
        100.0 * recorded_minutes
        / NULLIF(SUM(recorded_minutes) OVER (PARTITION BY week_start), 0),
        1
    ) AS pct_of_weeks_recorded_minutes
FROM weekly
ORDER BY week_start DESC, time_rank, activity;
"""


# Compare each activity's logged and unlogged days, separately for same-day and
# next-calendar-day stress. Baseline dates must have at least one activity log.
# One row per activity/date prevents repeated entries from weighting a day twice.
# These are descriptive associations; unlogged does not mean not performed.
activity_stress_comparison = "WITH " + _STRESS_CTES + """,
activity_days AS (
    SELECT DISTINCT log_date, activity_id
    FROM activity_log
),
logged_dates AS (
    SELECT DISTINCT log_date
    FROM activity_days
),
observed_activities AS (
    SELECT DISTINCT a.activity_id, a.name AS activity
    FROM activity a
    JOIN activity_days d USING (activity_id)
),
comparisons AS (
    SELECT
        a.activity,
        timing.stress_timing,
        s.category,
        present.activity_id IS NOT NULL AS activity_logged,
        s.score
    FROM observed_activities a
    CROSS JOIN logged_dates d
    CROSS JOIN LATERAL (
        VALUES
            ('Same day', d.log_date),
            ('Next day', d.log_date + 1)
    ) AS timing(stress_timing, stress_date)
    LEFT JOIN activity_days present
        ON present.activity_id = a.activity_id
       AND present.log_date = d.log_date
    JOIN stress_observations s ON s.log_date = timing.stress_date
    WHERE s.score IS NOT NULL
),
summary AS (
    SELECT
        activity,
        stress_timing,
        category,
        COUNT(*) FILTER (WHERE activity_logged) AS days_activity_logged,
        COUNT(*) FILTER (WHERE NOT activity_logged) AS days_activity_not_logged,
        AVG(score) FILTER (WHERE activity_logged) AS score_when_logged,
        AVG(score) FILTER (WHERE NOT activity_logged) AS score_when_not_logged
    FROM comparisons
    GROUP BY activity, stress_timing, category
)
SELECT
    activity,
    stress_timing,
    category,
    days_activity_logged,
    days_activity_not_logged,
    ROUND(score_when_logged, 2) AS average_score_when_logged,
    ROUND(score_when_not_logged, 2) AS average_score_when_not_logged,
    ROUND(score_when_logged - score_when_not_logged, 2) AS score_difference,
    CASE
        WHEN days_activity_logged = 0 OR days_activity_not_logged = 0
            THEN 'No comparison group'
        WHEN days_activity_logged < 5 OR days_activity_not_logged < 5
            THEN 'Fewer than 5 days in a group'
        ELSE 'At least 5 days in each group'
    END AS sample_size_note
FROM summary
ORDER BY activity, stress_timing, category;
"""


# Associate sleep with the day you wake up, explicitly in Indianapolis time.
# Use the longest complete session ending on each date to avoid counting naps
# or multiple sleep records as multiple stress days. Buckets are descriptive.
sleep_stress_productivity = "WITH " + _STRESS_CTES + """,
sleep_sessions AS (
    SELECT
        sleep_log_id,
        (wake_time AT TIME ZONE 'America/Indiana/Indianapolis')::date AS wake_date,
        bedtime,
        EXTRACT(EPOCH FROM (wake_time - bedtime)) / 60 AS minutes_in_bed,
        EXTRACT(EPOCH FROM (wake_time - bedtime)) / 60
            - COALESCE(total_interruption_minutes, 0) AS sleep_minutes
    FROM sleep_log
    WHERE bedtime IS NOT NULL AND wake_time IS NOT NULL
),
ranked_sleep AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY wake_date
        ORDER BY minutes_in_bed DESC, bedtime DESC, sleep_log_id DESC
    ) AS session_rank
    FROM sleep_sessions
    WHERE minutes_in_bed > 0 AND sleep_minutes >= 0
),
matched AS (
    SELECT
        CASE
            WHEN l.sleep_minutes < 360 THEN 'Under 6 hours'
            WHEN l.sleep_minutes < 420 THEN '6 to under 7 hours'
            WHEN l.sleep_minutes < 480 THEN '7 to under 8 hours'
            ELSE '8 hours or more'
        END AS sleep_band,
        CASE
            WHEN l.sleep_minutes < 360 THEN 1
            WHEN l.sleep_minutes < 420 THEN 2
            WHEN l.sleep_minutes < 480 THEN 3
            ELSE 4
        END AS band_order,
        l.sleep_minutes,
        d.*,
        p.work_productivity_level
    FROM ranked_sleep l
    JOIN stress_daily d ON d.log_date = l.wake_date
    JOIN stress_log p ON p.log_date = d.log_date
    WHERE l.session_rank = 1
)
SELECT
    sleep_band,
    COUNT(*) AS matched_days,
    ROUND(AVG(sleep_minutes) / 60, 2) AS average_sleep_hours,
    COUNT(work_score) AS work_stress_days,
    ROUND(AVG(work_score), 2) AS average_work_stress,
    COUNT(family_score) AS family_stress_days,
    ROUND(AVG(family_score), 2) AS average_family_stress,
    COUNT(health_score) AS health_stress_days,
    ROUND(AVG(health_score), 2) AS average_health_stress,
    COUNT(other_score) AS other_stress_days,
    ROUND(AVG(other_score), 2) AS average_other_stress,
    COUNT(*) FILTER (
        WHERE work_productivity_level IN (
            'Very Unproductive', 'Unproductive', 'Slightly Productive',
            'Moderately Productive', 'Highly Productive', 'Exceptionally Productive'
        )
    ) AS productivity_days,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE work_productivity_level IN (
                'Highly Productive', 'Exceptionally Productive'
            )
        ) / NULLIF(COUNT(*) FILTER (
            WHERE work_productivity_level IN (
                'Very Unproductive', 'Unproductive', 'Slightly Productive',
                'Moderately Productive', 'Highly Productive', 'Exceptionally Productive'
            )
        ), 0),
        1
    ) AS highly_productive_pct
FROM matched
GROUP BY sleep_band, band_order
ORDER BY band_order;
"""


# Distribution of productivity labels within each recorded work stress level.
# No Work is excluded independently from both fields; no score is assigned to it.
stress_productivity_patterns = "WITH " + _STRESS_CTES + """,
productivity_scale(label, score) AS (
    VALUES
        ('Very Unproductive', 1),
        ('Unproductive', 2),
        ('Slightly Productive', 3),
        ('Moderately Productive', 4),
        ('Highly Productive', 5),
        ('Exceptionally Productive', 6)
),
counts AS (
    SELECT
        s.work_stress_level,
        stress.score AS stress_order,
        s.work_productivity_level,
        productivity.score AS productivity_order,
        COUNT(*) AS days
    FROM stress_log s
    JOIN stress_scale stress ON stress.label = s.work_stress_level
    JOIN productivity_scale productivity
        ON productivity.label = s.work_productivity_level
    GROUP BY
        s.work_stress_level, stress.score,
        s.work_productivity_level, productivity.score
)
SELECT
    work_stress_level,
    work_productivity_level,
    days,
    SUM(days) OVER (PARTITION BY work_stress_level) AS days_at_this_stress_level,
    ROUND(
        100.0 * days / SUM(days) OVER (PARTITION BY work_stress_level), 1
    ) AS pct_within_stress_level
FROM counts
ORDER BY stress_order, productivity_order DESC;
"""

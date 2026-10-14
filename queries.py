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
    """Return a row-oriented SQL summary for every wellness log on one date."""
    log_date = Date.fromisoformat(str(log_date)).isoformat()
    return f"""
WITH params AS (
    SELECT DATE '{log_date}' AS log_date
),
food_totals AS (
    SELECT
        p.log_date,
        COUNT(fl.food_log_id)::numeric AS food_log_rows,
        COALESCE(SUM(
            f.calories * fl.quantity *
            CASE WHEN fl.combo_name IS NOT NULL THEN ac.serving_size ELSE 1 END
        ), 0) AS calories,
        COALESCE(SUM(
            f.carbohydrates * fl.quantity *
            CASE WHEN fl.combo_name IS NOT NULL THEN ac.serving_size ELSE 1 END
        ), 0) AS carbohydrates,
        COALESCE(SUM(
            f.proteins * fl.quantity *
            CASE WHEN fl.combo_name IS NOT NULL THEN ac.serving_size ELSE 1 END
        ), 0) AS proteins,
        COALESCE(SUM(
            f.fats * fl.quantity *
            CASE WHEN fl.combo_name IS NOT NULL THEN ac.serving_size ELSE 1 END
        ), 0) AS fats,
        COALESCE(SUM(
            f.fiber * fl.quantity *
            CASE WHEN fl.combo_name IS NOT NULL THEN ac.serving_size ELSE 1 END
        ), 0) AS fiber
    FROM params p
    LEFT JOIN food_log fl
        ON fl.log_date = p.log_date
    LEFT JOIN food f
        ON f.food_id = fl.food_id
    LEFT JOIN all_combos ac
        ON ac.food_id = fl.food_id
       AND ac.combo_name = '-' || fl.combo_name
    GROUP BY p.log_date
),
exercise_totals AS (
    SELECT
        p.log_date,
        COUNT(el.exercise_log_id) AS entries,
        COALESCE(SUM(el.duration_minutes), 0) AS total_duration_minutes
    FROM params p
    LEFT JOIN exercise_log el
        ON el.log_date = p.log_date
    GROUP BY p.log_date
),
activity_totals AS (
    SELECT
        p.log_date,
        COUNT(al.activity_log_id) AS entries,
        COALESCE(SUM(al.duration_minutes), 0) AS total_duration_minutes
    FROM params p
    LEFT JOIN activity_log al
        ON al.log_date = p.log_date
    GROUP BY p.log_date
)

SELECT
    ft.log_date,
    'food'::text AS section,
    v.item,
    ROUND(v.amount, 1)::text AS value,
    v.unit,
    NULL::jsonb AS details
FROM food_totals ft
CROSS JOIN LATERAL (
    VALUES
        ('food_log_rows', ft.food_log_rows, 'rows'),
        ('calories', ft.calories, 'kcal'),
        ('carbohydrates', ft.carbohydrates, 'g'),
        ('proteins', ft.proteins, 'g'),
        ('fats', ft.fats, 'g'),
        ('fiber', ft.fiber, 'g')
) AS v(item, amount, unit)

UNION ALL

SELECT
    fl.log_date,
    'food'::text AS section,
    fl.meal_type || ': ' || f.name AS item,
    fl.quantity::text AS value,
    COALESCE(f.measurement_unit, 'serving') AS unit,
    jsonb_build_object(
        'food_log_id', fl.food_log_id,
        'combo_name', fl.combo_name,
        'combo_component_servings', ac.serving_size,
        'calories', ROUND(
            f.calories * fl.quantity *
            CASE WHEN fl.combo_name IS NOT NULL THEN ac.serving_size ELSE 1 END, 1
        ),
        'carbohydrates', ROUND(
            f.carbohydrates * fl.quantity *
            CASE WHEN fl.combo_name IS NOT NULL THEN ac.serving_size ELSE 1 END, 1
        ),
        'proteins', ROUND(
            f.proteins * fl.quantity *
            CASE WHEN fl.combo_name IS NOT NULL THEN ac.serving_size ELSE 1 END, 1
        ),
        'fats', ROUND(
            f.fats * fl.quantity *
            CASE WHEN fl.combo_name IS NOT NULL THEN ac.serving_size ELSE 1 END, 1
        ),
        'fiber', ROUND(
            f.fiber * fl.quantity *
            CASE WHEN fl.combo_name IS NOT NULL THEN ac.serving_size ELSE 1 END, 1
        ),
        'notes', fl.notes
    ) AS details
FROM food_log fl
JOIN params p
    ON p.log_date = fl.log_date
JOIN food f
    ON f.food_id = fl.food_id
LEFT JOIN all_combos ac
    ON ac.food_id = fl.food_id
   AND ac.combo_name = '-' || fl.combo_name

UNION ALL

SELECT
    et.log_date,
    'exercise'::text AS section,
    'daily_total'::text AS item,
    et.entries::text AS value,
    'entries'::text AS unit,
    jsonb_build_object(
        'total_duration_minutes', et.total_duration_minutes
    ) AS details
FROM exercise_totals et

UNION ALL

SELECT
    el.log_date,
    'exercise'::text AS section,
    e.name AS item,
    el.duration_minutes::text AS value,
    'minutes'::text AS unit,
    jsonb_build_object(
        'exercise_log_id', el.exercise_log_id,
        'exercise_type', e.exercise_type,
        'notes', el.notes,
        'created_at_utc', el.created_at_utc
    ) AS details
FROM exercise_log el
JOIN params p
    ON p.log_date = el.log_date
JOIN exercise e
    ON e.exercise_id = el.exercise_id

UNION ALL

SELECT
    at.log_date,
    'activity'::text AS section,
    'daily_total'::text AS item,
    at.entries::text AS value,
    'entries'::text AS unit,
    jsonb_build_object(
        'total_duration_minutes', at.total_duration_minutes
    ) AS details
FROM activity_totals at

UNION ALL

SELECT
    al.log_date,
    'activity'::text AS section,
    a.name AS item,
    al.duration_minutes::text AS value,
    'minutes'::text AS unit,
    jsonb_build_object(
        'activity_log_id', al.activity_log_id,
        'notes', al.notes,
        'created_at_utc', al.created_at_utc
    ) AS details
FROM activity_log al
JOIN params p
    ON p.log_date = al.log_date
JOIN activity a
    ON a.activity_id = al.activity_id

UNION ALL

SELECT
    s.log_date,
    'stress'::text AS section,
    'daily_stress'::text AS item,
    NULL::text AS value,
    NULL::text AS unit,
    jsonb_build_object(
        'work_stress_level', s.work_stress_level,
        'work_productivity_level', s.work_productivity_level,
        'family_stress_level', s.family_stress_level,
        'health_stress_level', s.health_stress_level,
        'other_stress_level', s.other_stress_level,
        'notes', s.notes
    ) AS details
FROM stress_log s
JOIN params p
    ON p.log_date = s.log_date

UNION ALL

SELECT
    sl.log_date,
    'sleep'::text AS section,
    'sleep_record'::text AS item,
    NULL::text AS value,
    NULL::text AS unit,
    jsonb_build_object(
        'bedtime', sl.bedtime,
        'wake_time', sl.wake_time,
        'duration_hours',
            CASE
                WHEN sl.bedtime IS NOT NULL AND sl.wake_time IS NOT NULL
                THEN ROUND(
                    (EXTRACT(EPOCH FROM (sl.wake_time - sl.bedtime)) / 3600)::numeric, 2
                )
            END,
        'interruptions', sl.interruptions,
        'total_interruption_minutes', sl.total_interruption_minutes,
        'notes', sl.notes
    ) AS details
FROM sleep_log sl
JOIN params p
    ON p.log_date = sl.log_date

UNION ALL

SELECT
    h.log_date,
    'hygiene'::text AS section,
    'daily_hygiene'::text AS item,
    NULL::text AS value,
    NULL::text AS unit,
    jsonb_build_object(
        'brushed', h.brushed,
        'flossed', h.flossed,
        'showered', h.showered,
        'brushed_time', h.brushed_time,
        'flossed_time', h.flossed_time,
        'shower_time', h.shower_time,
        'notes', h.notes
    ) AS details
FROM hygiene_log h
JOIN params p
    ON p.log_date = h.log_date

UNION ALL

SELECT
    w.log_date,
    'weather'::text AS section,
    'daily_weather'::text AS item,
    NULL::text AS value,
    NULL::text AS unit,
    jsonb_build_object(
        'temp_min_f', w.temp_min_f,
        'temp_max_f', w.temp_max_f,
        'humidity_level', w.humidity_level,
        'conditions', w.conditions,
        'notes', w.notes
    ) AS details
FROM weather_log w
JOIN params p
    ON p.log_date = w.log_date

UNION ALL

SELECT
    wl.log_date,
    'water'::text AS section,
    'total_consumed'::text AS item,
    wl.total_oz::text AS value,
    'oz'::text AS unit,
    NULL::jsonb AS details
FROM water_log wl
JOIN params p
    ON p.log_date = wl.log_date

UNION ALL

SELECT
    bm.log_date,
    'body_measurements'::text AS section,
    'daily_measurement'::text AS item,
    NULL::text AS value,
    NULL::text AS unit,
    jsonb_build_object(
        'weight_lbs', bm.weight_lbs,
        'waist_inches', bm.waist_inches
    ) AS details
FROM body_measurements bm
JOIN params p
    ON p.log_date = bm.log_date

ORDER BY section, item;
"""
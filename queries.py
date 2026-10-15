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
)
SELECT section, name, measure, details
FROM summary_rows
ORDER BY
    LOWER(REGEXP_REPLACE(section, ' TOTAL$', '')),
    section LIKE '% TOTAL',
    name;
"""
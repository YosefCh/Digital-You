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
        ROUND(ac.serving_size, 1) AS qty_in_combo,

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
agg_food = """
           SELECT
                   l.meal_type,
                   SUM(
                       f.carbohydrates * l.quantity *
                       CASE
                           WHEN l.combo_name IS NOT NULL THEN ac.serving_size
                           ELSE 1
                       END
                   ) AS carbs,
           
                   SUM(
                       f.proteins * l.quantity *
                       CASE
                           WHEN l.combo_name IS NOT NULL THEN ac.serving_size
                           ELSE 1
                       END
                   ) AS proteins,
           
                   SUM(
                       f.fats * l.quantity *
                       CASE
                           WHEN l.combo_name IS NOT NULL THEN ac.serving_size
                           ELSE 1
                       END
                   ) AS fats,
           
                   SUM(
                       f.fiber * l.quantity *
                       CASE
                           WHEN l.combo_name IS NOT NULL THEN ac.serving_size
                           ELSE 1
                       END
                   ) AS fiber,
           
                   SUM(
                       f.calories * l.quantity *
                       CASE
                           WHEN l.combo_name IS NOT NULL THEN ac.serving_size
                           ELSE 1
                       END
                   ) AS calories
           
               FROM food_log l
               LEFT JOIN food f
                   ON f.food_id = l.food_id
               LEFT JOIN all_combos ac
                   ON f.food_id = ac.food_id
               where l.log_date = DATE '2026-09-24'
               GROUP BY l.meal_type
               ORDER BY l.meal_type;             
           """
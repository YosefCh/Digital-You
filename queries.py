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
import pandas as pd
from IPython.display import display, HTML, Markdown
import json
from postgres import get_connection, run_select, run_ddl_dml

class WellnessTracker:
    def __init__(self):
        self.conn = get_connection()

    def insert_food_log(self, food_name, meal_type, quantity, log_date=None):
        
        # Determine if the food_name is a combo (starts with a dash) or a single food item
        if food_name.startswith("-"):
            food_name = food_name[1:]  # Remove the leading dash to get the combo name
            
            # query when user is not overriding the log_date (date is today's date)
            if log_date is None:
                self.query =  f"""
                INSERT INTO food_log (food_id, meal_type, quantity, combo_name)
                SELECT food_id, %s, %s, %s
                FROM {food_name}; """
                params = (meal_type, quantity, food_name)
            
            # query when user is overriding the log_date (i.e., providing a specific date. For example, if they are logging a meal from yesterday or last week)     
            else:
                self.query =  f"""
                INSERT INTO food_log (log_date, food_id, meal_type, quantity, combo_name)
                SELECT %s, food_id, %s, %s, %s
                FROM {food_name}; """
                params = (log_date, meal_type, quantity, food_name)
        
        # query when the food_name is a single food item (not a combo)
        else:
            if log_date is None:
                self.query = """
                INSERT INTO food_log (food_id, meal_type, quantity)
                SELECT f.food_id, %s, %s
                FROM food f
                WHERE f.name = %s
            """
                params = (meal_type, quantity, food_name)
            else:
                self.query = """
                INSERT INTO food_log (log_date, food_id, meal_type, quantity)
                SELECT %s, f.food_id, %s, %s
                FROM food f
                WHERE f.name = %s
            """
                params = (log_date, meal_type, quantity, food_name)
 
        
        affected = run_ddl_dml(self.query, params=params)
        if affected is None:
            raise RuntimeError("Insert failed: database did not return an affected rowcount.")
        if affected <= 0:
            raise ValueError(f"Insert failed for name={food_name!r} (affected={affected}).")
        
    def insert_exercise_log(
        self,
        exercise_type: str,
        exercise_name: str,
        duration_minutes: int | None = None,
        notes: str | None = None,
        log_date=None,
        ):
        """
        Insert an exercise log row by resolving exercise_id from (exercise_type, name).
        - log_date=None uses the table default (CURRENT_DATE)
        """

        if log_date is None:
            self.query = """
                INSERT INTO exercise_log (exercise_id, duration_minutes, notes)
                SELECT e.exercise_id, %s, %s
                FROM exercise e
                WHERE e.exercise_type = %s
                  AND e.name = %s
            """
            params = (duration_minutes, notes, exercise_type, exercise_name)
        else:
            self.query = """
                INSERT INTO exercise_log (log_date, exercise_id, duration_minutes, notes)
                SELECT %s, e.exercise_id, %s, %s
                FROM exercise e
                WHERE e.exercise_type = %s
                  AND e.name = %s
            """
            params = (log_date, duration_minutes, notes, exercise_type, exercise_name)

        affected = run_ddl_dml(self.query, params=params)
        if affected is None:
            raise RuntimeError("Insert failed: database did not return an affected rowcount.")
        if affected <= 0:
            raise ValueError(
                f"Insert failed for exercise_type={exercise_type!r}, name={exercise_name!r} (affected={affected})."
            )
            
    def insert_activity_log(
        self,
        activity_name: str,
        duration_minutes: int | None = None,
        notes: str | None = None,
        log_date=None,
        ):
        """
        Insert an activity log row by resolving activity_id from activity.name.
        - log_date=None uses the table default (CURRENT_DATE)
        """

        if log_date is None:
            self.query = """
                INSERT INTO activity_log (activity_id, duration_minutes, notes)
                SELECT a.activity_id, %s, %s
                FROM activity a
                WHERE a.name = %s
            """
            params = (duration_minutes, notes, activity_name)
        else:
            self.query = """
                INSERT INTO activity_log (log_date, activity_id, duration_minutes, notes)
                SELECT %s, a.activity_id, %s, %s
                FROM activity a
                WHERE a.name = %s
            """
            params = (log_date, duration_minutes, notes, activity_name)

        affected = run_ddl_dml(self.query, params=params)
        if affected is None:
            raise RuntimeError("Insert failed: database did not return an affected rowcount.")
        if affected <= 0:
            raise ValueError(f"Insert failed for activity_name={activity_name!r} (affected={affected}).")
        
        
    

    def insert_stress_log(
        self,
        work_stress_level: int | None = None,
        work_productivity_level: int | None = None,
        family_stress_level: int | None = None,
        health_stress_level: int | None = None,
        other_stress_level: int | None = None,
        notes: str | None = None,
        log_date=None,
        ):
        """
        Insert a stress_log row.
        - log_date=None uses the table default (CURRENT_DATE)
        - Will raise an error if a row already exists for that log_date (UNIQUE constraint).
        """

        if log_date is None:
            self.query = """
                INSERT INTO stress_log
                    (
                        work_stress_level,
                        work_productivity_level,
                        family_stress_level,
                        health_stress_level,
                        other_stress_level,
                        notes
                    )
                VALUES
                    (%s, %s, %s, %s, %s, %s)
            """
            params = (
                work_stress_level,
                work_productivity_level,
                family_stress_level,
                health_stress_level,
                other_stress_level,
                notes,
            )
        else:
            self.query = """
                INSERT INTO stress_log
                    (
                        log_date,
                        work_stress_level,
                        work_productivity_level,
                        family_stress_level,
                        health_stress_level,
                        other_stress_level,
                        notes
                    )
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                log_date,
                work_stress_level,
                work_productivity_level,
                family_stress_level,
                health_stress_level,
                other_stress_level,
                notes,
            )

        affected = run_ddl_dml(self.query, params=params)
        if affected is None:
            raise RuntimeError("Insert failed: database did not return an affected rowcount.")
        if affected <= 0:
            raise ValueError(f"Insert failed for stress_log (log_date={log_date!r}, affected={affected}).")
    
    
    def insert_sleep_log(
        self,
        bedtime=None,                 # TIMESTAMPTZ
        wake_time=None,               # TIMESTAMPTZ
        interruptions: int | None = None,
        total_interruption_minutes: int | None = None,
        notes: str | None = None,
        log_date=None,
    ):
        """
        Insert a sleep_log row.
        - log_date=None uses the table default (CURRENT_DATE)
        """

        if log_date is None:
            self.query = """
                INSERT INTO sleep_log
                    (bedtime, wake_time, interruptions, total_interruption_minutes, notes)
                VALUES
                    (%s, %s, %s, %s, %s)
            """
            params = (bedtime, wake_time, interruptions, total_interruption_minutes, notes)
        else:
            self.query = """
                INSERT INTO sleep_log
                    (log_date, bedtime, wake_time, interruptions, total_interruption_minutes, notes)
                VALUES
                    (%s, %s, %s, %s, %s, %s)
            """
            params = (log_date, bedtime, wake_time, interruptions, total_interruption_minutes, notes)

        affected = run_ddl_dml(self.query, params=params)
        if affected is None:
            raise RuntimeError("Insert failed: database did not return an affected rowcount.")
        if affected <= 0:
            raise ValueError(f"Insert failed for sleep_log (log_date={log_date!r}, affected={affected}).")


    def insert_water_log(
        self,
        total_oz: float,
        log_date=None,
    ):
        """
        Insert a water_log row.
        - log_date=None uses the table default (CURRENT_DATE)
        - One row per day (UNIQUE(log_date))
        """

        if log_date is None:
            self.query = """
                INSERT INTO water_log
                    (total_oz)
                VALUES
                    (%s)
            """
            params = (total_oz,)
        else:
            self.query = """
                INSERT INTO water_log
                    (log_date, total_oz)
                VALUES
                    (%s, %s)
            """
            params = (log_date, total_oz)

        affected = run_ddl_dml(self.query, params=params)
        if affected is None:
            raise RuntimeError("Insert failed: database did not return an affected rowcount.")
        if affected <= 0:
            raise ValueError(f"Insert failed for water_log (log_date={log_date!r}, affected={affected}).")


    def insert_weather_log(
        self,
        temp_min_f: float | None = None,
        temp_max_f: float | None = None,
        humidity_level: str | None = None,   # 'Low'|'Moderate'|'High'
        conditions: str | None = None,
        notes: str | None = None,
        log_date=None,
    ):
        """
        Insert a weather_log row.
        - log_date=None uses the table default (CURRENT_DATE)
        - One row per day (UNIQUE(log_date))
        """

        if log_date is None:
            self.query = """
                INSERT INTO weather_log
                    (temp_min_f, temp_max_f, humidity_level, conditions, notes)
                VALUES
                    (%s, %s, %s, %s, %s)
            """
            params = (temp_min_f, temp_max_f, humidity_level, conditions, notes)
        else:
            self.query = """
                INSERT INTO weather_log
                    (log_date, temp_min_f, temp_max_f, humidity_level, conditions, notes)
                VALUES
                    (%s, %s, %s, %s, %s, %s)
            """
            params = (log_date, temp_min_f, temp_max_f, humidity_level, conditions, notes)

        affected = run_ddl_dml(self.query, params=params)
        if affected is None:
            raise RuntimeError("Insert failed: database did not return an affected rowcount.")
        if affected <= 0:
            raise ValueError(f"Insert failed for weather_log (log_date={log_date!r}, affected={affected}).")
    
    
    def insert_hygiene_log(
        self,
        brushed: bool = False,
        flossed: bool = False,
        showered: bool = False,
        brushed_time: str | None = None,
        flossed_time: str | None = None,
        shower_time: str | None = None,
        notes: str | None = None,
        log_date=None,
    ):
        """
        Insert a hygiene_log row.
        - log_date=None uses the table default (CURRENT_DATE)
        - One row per day (UNIQUE(log_date))
        """
        if log_date is None:
            self.query = """
                INSERT INTO hygiene_log
                    (brushed, flossed, showered, brushed_time, flossed_time, shower_time, notes)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (brushed, flossed, showered, brushed_time, flossed_time, shower_time, notes)
        else:
            self.query = """
                INSERT INTO hygiene_log
                    (log_date, brushed, flossed, showered, brushed_time, flossed_time, shower_time, notes)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (log_date, brushed, flossed, showered, brushed_time, flossed_time, shower_time, notes)

        affected = run_ddl_dml(self.query, params=params)
        if affected is None:
            raise RuntimeError("Insert failed: database did not return an affected rowcount.")
        if affected <= 0:
            raise ValueError(f"Insert failed for hygiene_log (log_date={log_date!r}, affected={affected}).")
    
    
    def insert_measurements_log(
            self,
            log_date=None,
            weight_lbs: float | None = None,
            waist_inches: float | None = None,
        ):
            """
            Insert a measurements_log row.
            - log_date=None uses the table default (CURRENT_DATE)
            - One row per day (UNIQUE(log_date))
            """
            if log_date is None:
                self.query = """
                    INSERT INTO body_measurements
                        (weight_lbs, waist_inches)
                    VALUES
                        (%s, %s)
                """
                params = (weight_lbs, waist_inches)
            else:
                self.query = """
                    INSERT INTO body_measurements
                        (log_date, weight_lbs, waist_inches)
                    VALUES
                        (%s, %s, %s)
                """
                params = (log_date, weight_lbs, waist_inches)
    
            affected = run_ddl_dml(self.query, params=params)
            if affected is None:
                raise RuntimeError("Insert failed: database did not return an affected rowcount.")
            if affected <= 0:
                raise ValueError(f"Insert failed for body_measurements (log_date={log_date!r}, affected={affected}).")
    
    def insert_new_food(
        self,
        name: str,
        calories: float,
        carbohydrates: float,
        proteins: float,
        fats: float,
        fiber: float,
        serving_size: float,
        measurement_unit: str,
    ):
        """
        Insert a food row, or update an existing row if a case-insensitive match is found.
        Numeric inputs are rounded to two decimals before insert/update.
        """
        name = (name or "").strip()
        if not name:
            raise ValueError("Food name is required.")

        required = {
            "calories": calories,
            "carbohydrates": carbohydrates,
            "proteins": proteins,
            "fats": fats,
            "fiber": fiber,
            "serving_size": serving_size,
        }
        for key, value in required.items():
            if value is None:
                raise ValueError(f"{key} is required and cannot be None.")

        if calories is None or calories <= 0:
            raise ValueError("calories must be greater than 0.")
        if serving_size is None or serving_size <= 0:
            raise ValueError("serving_size must be greater than 0.")

        if carbohydrates == 0 and proteins == 0 and fats == 0:
            raise ValueError("At least one of carbohydrates, proteins, or fats must be greater than 0.")

        calories = round(float(calories), 2)
        carbohydrates = round(float(carbohydrates), 2)
        proteins = round(float(proteins), 2)
        fats = round(float(fats), 2)
        fiber = round(float(fiber), 2)
        serving_size = round(float(serving_size), 2)
        measurement_unit = (measurement_unit or "").strip()

        safe_name = name.replace("'", "''")
        
        # check if a food with the same name (case-insensitive) already exists in the database
        select_query = f"""
            SELECT food_id
            FROM food
            WHERE lower(name) = lower('{safe_name}')
            LIMIT 1;
        """
        rows, _ = run_select(select_query, return_df=False)

        if rows:
          
            food_id = rows[0][0]
            update_query = """
                UPDATE food
                SET name = %s,
                    calories = %s,
                    carbohydrates = %s,
                    proteins = %s,
                    fats = %s,
                    fiber = %s,
                    serving_size = %s,
                    measurement_unit = %s
                WHERE food_id = %s;
            """
            params = (
                name,
                calories,
                carbohydrates,
                proteins,
                fats,
                fiber,
                serving_size,
                measurement_unit,
                food_id,
            )
            affected = run_ddl_dml(update_query, params=params)
            return 1 if affected is None else affected

        insert_query = """
            INSERT INTO food
                (name, calories, carbohydrates, proteins, fats, fiber, serving_size, measurement_unit)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        params = (
            name,
            calories,
            carbohydrates,
            proteins,
            fats,
            fiber,
            serving_size,
            measurement_unit,
        )
        affected = run_ddl_dml(insert_query, params=params)
        return 1 if affected is None else affected

    def create_combo_view(self, combo_name: str, food_names: list, food_servings: list):
        """
        Create a combo view for the specified food items.
        """
        
        # remove leading & trailing spaces and replace spaces with underscores. this is needed for a proper view name
        # Precede with dash and convert to uppercase to standout in food dropdown
        combo_name_in_view = "-" +  "_".join(combo_name.upper().strip().split()) 
        

        # get first chars of all chosen foods to check if existing combos are part of the new combo
        first_chars = [i[0] for i in food_names]
        union_delim = "\n\t\tUNION ALL\n"
        # check for telltale sign of a combo (-)
        if first_chars.count('-') < 1:
            # if no chosen foods are existing combos
            union_sql = union_delim.join(
                f"""
                SELECT '{combo_name_in_view}' AS combo_name, food_id, '{food_name}' AS name, {serving}::NUMERIC(10,2) AS serving_size
                FROM food
                WHERE name = '{food_name}'
                """
                for food_name, serving in zip(food_names, food_servings)
                )
            
        elif first_chars.count('-') == len(first_chars):
            # if all chosen foods are combos
            union_sql = union_delim.join(
                f"""
                SELECT '{combo_name_in_view}' AS combo_name, food_id, name, serving_size::NUMERIC(10,2) AS serving_size
                FROM {combo[1:]}
                """
                for combo in food_names)
               
        else:
            # if the chosen foods contain both plain foods and combos
            # pair names and servings first so duplicates keep the correct association
            paired_choices = list(zip(food_names, food_servings))

            chosen_foods = [pair for pair in paired_choices if not pair[0].startswith('-')]
            chosen_combos = [pair for pair in paired_choices if pair[0].startswith('-')]

            sql_part_1 = union_delim.join(
                f"""
                SELECT '{combo_name_in_view}' AS combo_name, food_id, '{food_name}' AS name, {serving}::NUMERIC(10,2) AS serving_size
                FROM food
                WHERE name = '{food_name}'
                """
                for food_name, serving in chosen_foods
                )
           
            sql_part_2 = union_delim.join(
                f"""
                SELECT '{combo_name_in_view}' AS combo_name, food_id, name, (serving_size::NUMERIC(10,2) * {combo_serving}::NUMERIC(10,2))::NUMERIC(10,2) AS serving_size
                FROM {combo_name[1:]}
                """
                for combo_name, combo_serving in chosen_combos
                )

            union_sql = sql_part_1 + union_delim + sql_part_2
        

        
               
        query = f"""
        CREATE OR REPLACE VIEW {combo_name_in_view[1:]} AS {union_sql}
                """ 
        
        drop_query = f"DROP VIEW IF EXISTS {combo_name_in_view[1:]} CASCADE;"
        run_ddl_dml(drop_query)
        
        print(query)
        
        
        # no need for params as user can only enter value from the existing dropdown
        affected = run_ddl_dml(query)   
        
        # For DDL, many drivers return None or a negative value; only treat an explicit zero as failure.
        if affected is not None and affected == 0:
            raise ValueError(f"View creation failed (affected={affected}).")
        else:
            print('View Created')
            
        # build the master view that unions all combo views together, so that the new combo is included in the master view
        # which makes join queries easier to write for the user   
        self.rebuild_all_combos_view()
          
            
    
    def rebuild_all_combos_view(self):
        """
        Rebuild the master view that unions all combo views together.
        """

        rows, _ = run_select(
            """
            SELECT viewname
            FROM pg_views
            WHERE schemaname = 'public'
            AND viewname <> 'all_combos'
            ORDER BY viewname;
            """,
            return_df=False
        )

        view_names = [row[0] for row in rows]

        # No combo views yet
        if not view_names:
            run_ddl_dml("""
                CREATE OR REPLACE VIEW all_combos AS
                SELECT
                    NULL::TEXT AS combo_name,
                    NULL::BIGINT AS food_id,
                    NULL::TEXT AS name,
                    NULL::NUMERIC(10,2) AS serving_size
                WHERE FALSE;
                """)
            return

        union_sql = "\nUNION ALL\n".join(
            f"""
            SELECT
                combo_name,
                food_id,
                name,
                serving_size
            FROM {view}
            """
            for view in view_names
            )

        query = f"""
        CREATE OR REPLACE VIEW all_combos AS
        {union_sql}
        """

        drop_query = "DROP VIEW IF EXISTS all_combos CASCADE;"
        run_ddl_dml(drop_query)
        run_ddl_dml(query)
    
    def insert_new_exercise(
        self,
        exercise_type: str,
        name: str,
    ):
        """
        Insert an exercise row, or update an existing row if a case-insensitive match is found
        for the same exercise type and name.
        """
        exercise_type = (exercise_type or "").strip()
        name = (name or "").strip()

        if not exercise_type:
            raise ValueError("Exercise type is required.")

        normalized_type = {
            "cardio": "Cardio",
            "strength": "Strength",
            "balance": "Balance",
            "mobility": "Mobility",
            "physical therapy": "Physical Therapy",
        }.get(exercise_type.lower(), exercise_type)

        if normalized_type not in {"Cardio", "Strength", "Balance", "Mobility", "Physical Therapy"}:
            raise ValueError("Exercise type must be one of: Cardio, Strength, Balance, Mobility, Physical Therapy.")
        if not name:
            raise ValueError("Exercise name is required.")

        safe_type = normalized_type.replace("'", "''")
        safe_name = name.replace("'", "''")

        select_query = f"""
            SELECT exercise_id
            FROM exercise
            WHERE lower(exercise_type) = lower('{safe_type}')
              AND lower(name) = lower('{safe_name}')
            LIMIT 1;
        """
        rows, _ = run_select(select_query, return_df=False)

        if rows:
            exercise_id = rows[0][0]
            update_query = """
                UPDATE exercise
                SET exercise_type = %s,
                    name = %s
                WHERE exercise_id = %s;
            """
            params = (normalized_type, name, exercise_id)
            affected = run_ddl_dml(update_query, params=params)
            return 1 if affected is None else affected

        insert_query = """
            INSERT INTO exercise
                (exercise_type, name)
            VALUES
                (%s, %s);
        """
        params = (normalized_type, name)
        affected = run_ddl_dml(insert_query, params=params)
        return 1 if affected is None else affected

    def insert_new_activity(
        self,
        name: str,
    ):
        """
        Insert an activity row, or update an existing row if a case-insensitive match is found.
        """
        name = (name or "").strip()

        if not name:
            raise ValueError("Activity name is required.")

        safe_name = name.replace("'", "''")

        select_query = f"""
            SELECT activity_id
            FROM activity
            WHERE lower(name) = lower('{safe_name}')
            LIMIT 1;
        """
        rows, _ = run_select(select_query, return_df=False)

        if rows:
            activity_id = rows[0][0]
            update_query = """
                UPDATE activity
                SET name = %s
                WHERE activity_id = %s;
            """
            params = (name, activity_id)
            affected = run_ddl_dml(update_query, params=params)
            return 1 if affected is None else affected

        insert_query = """
            INSERT INTO activity
                (name)
            VALUES
                (%s);
        """
        params = (name,)
        affected = run_ddl_dml(insert_query, params=params)
        return 1 if affected is None else affected


if __name__ == "__main__":
    tracker = WellnessTracker()
    # Example usage:
    # tracker.insert_food_log("Apple", "Breakfast", 1)
    # tracker.insert_exercise_log("Cardio", "Running", 30)
    # tracker.insert_activity_log("Meditation", 15)
    # tracker.insert_stress_log(work_stress_level=3, work_productivity_level=4)
    # tracker.insert_sleep_log(bedtime="2024-06-01 22:00:00", wake_time="2024-06-02 06:00:00")
    # tracker.insert_water_log(total_oz=64)
    # tracker.insert_weather_log(temp_min_f=60, temp_max_f=75, humidity_level="Moderate")
    # tracker.insert_hygiene_log(brushed=True, flossed=True, showered=True)
    # tracker.insert_measurements_log(weight_lbs=191.7, waist_inches=38.1)
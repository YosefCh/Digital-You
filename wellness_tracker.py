
import pandas as pd
import json
from postgres import get_connection, run_sql_file, run_select, run_ddl_dml

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
        
    
    def create_combo_view(self, combo_name: str, food_names: list, food_servings: list):
        """
        Create a combo view for the specified food items.
        """
        
        combo_name = combo_name.upper()  # Convert to uppercase for consistency in naming views.
        combo_name_in_view = '-' + combo_name.upper()  # Precede with dash and convert to uppercase for combo views to make them stand out in the food dropdown.
        
        union_sql = " UNION ALL ".join(
        f"""
        SELECT '{combo_name_in_view}' AS combo_name, food_id as food_id, '{food_name}' AS name, {serving} AS serving_size
        FROM food
        WHERE name ILIKE '%{food_name}%'
        """
        for food_name, serving in zip(food_names, food_servings)
        )   
               
        query = f"""
        CREATE OR REPLACE VIEW {combo_name} AS {union_sql}
                """ 
        
        # no need for params as user can only enter value from the existing dropdown
        affected = run_ddl_dml(query)   
        
        # For DDL, many drivers return None or a negative value; only treat an explicit zero as failure.
        if affected is not None and affected == 0:
            raise ValueError(f"View creation failed (affected={affected}).")
        else:
            print('View Created')
            
if __name__ == "__main__":
    tracker = WellnessTracker()

    
"""
DeleteLogEntry class for deleting individual entries from log tables.
Shows last 20-30 rows with JOINs to display readable names.
User selects row, confirms deletion.
"""

import ipywidgets as widgets
from IPython.display import display, HTML
from postgres import run_select, run_ddl_dml
from wellness_tracker import WellnessTracker


class DeleteLogEntry:
    """
    UI for deleting individual entries from log tables.
    Shows last 20-30 rows with JOINs to display readable names.
    User selects row, confirms deletion.
    """

    # Mapping of log table to (table_name, primary_key_column)
    LOG_TABLES = {
        "food_log": ("food_log", "food_log_id"),
        "exercise_log": ("exercise_log", "exercise_log_id"),
        "activity_log": ("activity_log", "activity_log_id"),
        "stress_log": ("stress_log", "stress_log_id"),
        "sleep_log": ("sleep_log", "sleep_log_id"),
        "weather_log": ("weather_log", "weather_log_id"),
        "water_log": ("water_log", "water_log_id"),
        "hygiene_log": ("hygiene_log", "hygiene_log_id"),
        "body_measurements": ("body_measurements", "body_measurement_id"),
    }

    def __init__(self):
        self.wt = WellnessTracker()
        self._inject_css()
        
        # Table selector
        self.table_selector = widgets.Dropdown(
            options=list(self.LOG_TABLES.keys()),
            value="food_log",
            description="Table:",
            style={"description_width": "80px"},
        )
        
        # Row selector (will be populated after table selection)
        self.row_selector = widgets.Dropdown(
            options=[],
            description="Row:",
            style={"description_width": "80px"},
        )
        
        # Confirmation button
        self.confirm_delete = widgets.Button(
            description="Confirm Delete",
            button_style="danger"
        )
        
        # Cancel button
        self.cancel_delete = widgets.Button(
            description="Cancel"
        )
        
        # Output area
        self.delete_out = widgets.Output()
        
        # Confirm box (hidden until row is selected)
        self.confirm_box = widgets.HBox([
            self.confirm_delete,
            self.cancel_delete
        ])
        self.confirm_box.layout.display = "none"
        
        # Main container
        self.ui_box = widgets.VBox([
            widgets.HTML("<b>Delete Log Entry</b>"),
            self.table_selector,
            self.row_selector,
            self.confirm_box,
            self.delete_out,
        ])
        
        self.ui_box.add_class("delete-widget-box")
        self._attach_handlers()

    def _inject_css(self):
        display(HTML("""
        <style>
        .delete-widget-box {
            background-color: rgb(1, 8, 35);
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 8px;
        }

        .delete-widget-box label.widget-label {
            font-weight: bold;
            color: rgb(190, 190, 190);
            font-size: 14px;
        }

        .delete-widget-box input,
        .delete-widget-box select {
            background-color: rgb(160, 170, 190) !important;
            border: 1px solid #99ccff !important;
            border-radius: 4px;
            color: rgb(1, 8, 15) !important;
            font-size: 13px;
        }

        .delete-widget-box input:focus,
        .delete-widget-box select:focus {
            border-color: #3366cc !important;
            box-shadow: 0 0 4px #3366cc !important;
            outline: none !important;
        }

        .delete-widget-box button {
            color: #ffffff !important;
            background-color: #006699 !important;
            border: 1px solid #004466 !important;
        }

        .delete-widget-box button:hover {
            background-color: #0088cc !important;
        }
        </style>
        """))

    def _attach_handlers(self):
        self.table_selector.observe(self._on_table_selected, names="value")
        self.row_selector.observe(self._on_row_selected, names="value")
        self.confirm_delete.on_click(self._on_confirm_delete)
        self.cancel_delete.on_click(self._on_cancel_delete)

    def _on_table_selected(self, change):
        """Load last 20-30 rows from selected table with JOINs."""
        selected_table = change["new"]
        self.delete_out.clear_output()
        self.confirm_box.layout.display = "none"
        self.row_selector.options = []
        
        with self.delete_out:
            display(HTML("<p style='color: gray;'>Loading rows...</p>"))
        
        try:
            # Get query based on selected table
            query = self._build_query_for_table(selected_table)
            rows_df = run_select(query, return_df=True)
            
            if rows_df.empty:
                self.delete_out.clear_output(wait=True)
                with self.delete_out:
                    display(HTML("<p style='color: orange;'>No rows found in this table.</p>"))
                return
            
            # Store the dataframe for later reference
            self.current_rows = rows_df
            self.current_table = selected_table
            
            # Build dropdown options with readable format
            options = self._format_rows_for_display(selected_table, rows_df)
            self.row_selector.options = options
            
            self.delete_out.clear_output(wait=True)
            with self.delete_out:
                display(HTML(f"<p style='color: green;'>Loaded {len(rows_df)} row(s).</p>"))
        
        except Exception as e:
            self.delete_out.clear_output(wait=True)
            with self.delete_out:
                display(HTML(f"<p style='color: red;'>Error loading rows: {str(e)}</p>"))

    def _on_row_selected(self, change):
        """Show confirmation button when a row is selected."""
        if self.row_selector.value:
            self.confirm_box.layout.display = ""
        else:
            self.confirm_box.layout.display = "none"

    def _on_confirm_delete(self, _):
        """Delete the selected row after confirmation."""
        self.confirm_delete.disabled = True
        
        try:
            selected_table = self.current_table
            selected_index = self.row_selector.index  # 0-based index into current_rows
            
            if selected_index is None or selected_index < 0:
                with self.delete_out:
                    display(HTML("<p style='color: red;'>No row selected.</p>"))
                return
            
            row = self.current_rows.iloc[selected_index]
            _, pk_column = self.LOG_TABLES[selected_table]
            row_id = int(row[pk_column])  # Convert numpy.int64 to Python int
            
            # Build and execute delete query
            delete_query = f"DELETE FROM {selected_table} WHERE {pk_column} = %s;"
            affected = run_ddl_dml(delete_query, params=(row_id,))
            
            # Show success message WITHOUT clearing output first (keeps it visible during refresh)
            with self.delete_out:
                display(HTML(f"<p style='color: green;'><b>✓ Deleted 1 row from {selected_table}</b></p>"))
            
            # Reset UI
            self.confirm_box.layout.display = "none"
            
            # Reload table data manually without clearing output (preserves success message)
            try:
                query = self._build_query_for_table(selected_table)
                df = run_select(query, return_df=True)
                self.current_rows = df
                self.current_table = selected_table
                
                # Update row dropdown with new options
                if len(df) > 0:
                    formatted_options = list(zip(self._format_rows_for_display(), range(len(df))))
                    self.row_selector.options = formatted_options
                else:
                    self.row_selector.options = []
            except Exception as reload_error:
                with self.delete_out:
                    display(HTML(f"<p style='color: red;'>Error reloading rows: {str(reload_error)}</p>"))
        
        except Exception as e:
            self.delete_out.clear_output(wait=True)
            with self.delete_out:
                display(HTML(f"<p style='color: red;'><b>Error deleting row:</b> {str(e)}</p>"))
        
        finally:
            self.confirm_delete.disabled = False

    def _on_cancel_delete(self, _):
        """Cancel deletion and hide confirmation box."""
        self.confirm_box.layout.display = "none"
        self.delete_out.clear_output()

    def _build_query_for_table(self, table_name):
        """
        Build SELECT query with JOINs to show readable names.
        Placeholder queries — customize per table with actual JOINs.
        """
        if table_name == "food_log":
            # PLACEHOLDER: JOIN food_log to food for food name, and optionally to combo view names
            return """
                SELECT fl.food_log_id, fl.log_date, fl.meal_type, f.name AS food_name, 
                       fl.quantity, fl.combo_name, fl.notes
                FROM food_log fl
                LEFT JOIN food f ON fl.food_id = f.food_id
                ORDER BY fl.log_date DESC
                LIMIT 30;
            """
        
        elif table_name == "exercise_log":
            # PLACEHOLDER: JOIN exercise_log to exercise for exercise name
            return """
                SELECT el.exercise_log_id, el.log_date, e.exercise_type, e.name AS exercise_name,
                       el.duration_minutes, el.notes
                FROM exercise_log el
                LEFT JOIN exercise e ON el.exercise_id = e.exercise_id
                ORDER BY el.log_date DESC
                LIMIT 30;
            """
        
        elif table_name == "activity_log":
            # PLACEHOLDER: JOIN activity_log to activity for activity name
            return """
                SELECT al.activity_log_id, al.log_date, a.name AS activity_name,
                       al.duration_minutes, al.notes
                FROM activity_log al
                LEFT JOIN activity a ON al.activity_id = a.activity_id
                ORDER BY al.log_date DESC
                LIMIT 30;
            """
        
        elif table_name == "stress_log":
            return """
                SELECT stress_log_id, log_date, work_stress_level, work_productivity_level,
                       family_stress_level, health_stress_level, other_stress_level, notes
                FROM stress_log
                ORDER BY log_date DESC
                LIMIT 30;
            """
        
        elif table_name == "sleep_log":
            return """
                SELECT sleep_log_id, log_date, bedtime, wake_time,
                       interruptions, total_interruption_minutes, notes
                FROM sleep_log
                ORDER BY log_date DESC
                LIMIT 30;
            """
        
        elif table_name == "weather_log":
            return """
                SELECT weather_log_id, log_date, temp_min_f, temp_max_f,
                       humidity_level, conditions, notes
                FROM weather_log
                ORDER BY log_date DESC
                LIMIT 30;
            """
        
        elif table_name == "water_log":
            return """
                SELECT water_log_id, log_date, total_oz
                FROM water_log
                ORDER BY log_date DESC
                LIMIT 30;
            """
        
        elif table_name == "hygiene_log":
            return """
                SELECT hygiene_log_id, log_date, brushed, brushed_time,
                       flossed, flossed_time, showered, shower_time, notes
                FROM hygiene_log
                ORDER BY log_date DESC
                LIMIT 30;
            """
        
        elif table_name == "body_measurements":
            return """
                SELECT body_measurement_id, log_date, weight_lbs, waist_inches
                FROM body_measurements
                ORDER BY log_date DESC
                LIMIT 30;
            """
        
        else:
            raise ValueError(f"Unknown table: {table_name}")

    def _format_rows_for_display(self, table_name, df):
        """
        Format dataframe rows into readable dropdown options.
        Each option is (display_text, index).
        """
        options = []
        
        for idx, row in df.iterrows():
            if table_name == "food_log":
                display_text = f"{row['log_date']} | {row['meal_type']} | {row['food_name'] or 'Unknown'} | {row['quantity']}"
            
            elif table_name == "exercise_log":
                display_text = f"{row['log_date']} | {row['exercise_type']} | {row['exercise_name'] or 'Unknown'} | {row['duration_minutes']} min"
            
            elif table_name == "activity_log":
                display_text = f"{row['log_date']} | {row['activity_name'] or 'Unknown'} | {row['duration_minutes']} min"
            
            elif table_name == "stress_log":
                display_text = f"{row['log_date']} | Work: {row['work_stress_level']} | Family: {row['family_stress_level']}"
            
            elif table_name == "sleep_log":
                bedtime_str = row['bedtime'].strftime("%H:%M") if row['bedtime'] else "N/A"
                wake_str = row['wake_time'].strftime("%H:%M") if row['wake_time'] else "N/A"
                display_text = f"{row['log_date']} | Bed: {bedtime_str} → Wake: {wake_str}"
            
            elif table_name == "weather_log":
                display_text = f"{row['log_date']} | Temp: {row['temp_min_f']}–{row['temp_max_f']}°F | {row['conditions']}"
            
            elif table_name == "water_log":
                display_text = f"{row['log_date']} | {row['total_oz']} oz"
            
            elif table_name == "hygiene_log":
                actions = []
                if row['brushed']:
                    actions.append(f"Brush({row['brushed_time']})")
                if row['flossed']:
                    actions.append(f"Floss({row['flossed_time']})")
                if row['showered']:
                    actions.append(f"Shower({row['shower_time']})")
                display_text = f"{row['log_date']} | {', '.join(actions) if actions else 'None'}"
            
            elif table_name == "body_measurements":
                display_text = f"{row['log_date']} | Weight: {row['weight_lbs']} lbs | Waist: {row['waist_inches']} in"
            
            else:
                display_text = str(row)
            
            options.append((display_text, idx))
        
        return options

    def display(self):
        display(self.ui_box)

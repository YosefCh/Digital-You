import ipywidgets as widgets
from IPython.display import display, HTML, Markdown
from datetime import date, datetime, time, timedelta
from postgres import run_select
from wellness_tracker import WellnessTracker
from AI import OpenAIClient

class UIFunctions:

    def __init__(self):
        self.wellness_tracker = WellnessTracker()
        self.openai_client = OpenAIClient()

    def get_view_combo_names(self):
        """
        This function retrieves the combo names of the views in order to add to the food dropdown widget. It queries the pg_views table to get 
        the names of all views in the public schema, then constructs a SQL query that unions the distinct combo_names from each view, and 
        finally returns a list of all combo names.
        """
        query = """
            SELECT viewname
            FROM pg_views
            WHERE schemaname = 'public'
            AND viewname <> 'all_combos'
            ORDER BY schemaname, viewname;
        """
        
        # use try except for program start when there might not be any views yet
        try:
            views = run_select(query, return_df=True)['viewname'].tolist()
            
            # create one SQL query that unions all the distinct combo_names from each view
            union_sql = " UNION ".join(
            f"SELECT DISTINCT combo_name AS name FROM {view}"
            for view in views
            )
            
            df = run_select(union_sql, return_df=True, show_errors=False)
            all_combo_names = df['name'].tolist()
            return all_combo_names
        except Exception:
            # print(f"Error retrieving combo names: {e}")
            return []
    
    def ui_insert_food(self):
        """
        This function creates a user interface for inserting food data into the wellness tracker. It retrieves the combo names of the views, 
        creates a dropdown widget for selecting a combo name, and a button for submitting the selected combo name. When the button is clicked, 
        it calls the insert_food method of the WellnessTracker class with the selected combo name.
        """
        
        
        # Build widget data
        all_foods = []
        views = (self.get_view_combo_names())
        all_foods.extend(views)

        reg_foods = run_select(
            """
            select name from food
            order by name;
            """,
            return_df=True,
        )['name'].tolist()

        all_foods.extend(reg_foods)

        foods = all_foods

        # Date handling
        override_date = widgets.Checkbox(
            description="Override date",
            value=False,
        )

        log_date = widgets.DatePicker(
            description="Log Date:",
            value=date.today(),
        )


        def _sync_date_visibility(*_):
            if override_date.value:
                log_date.layout.display = ""

                if log_date.value is None:
                    log_date.value = date.today()

            else:
                log_date.layout.display = "none"


        override_date.observe(_sync_date_visibility, names="value")
        _sync_date_visibility()


        food_search = widgets.Text(
            description="Search:",
            placeholder="Type to filter foods",
        )

        food = widgets.Dropdown(
            options=all_foods,
            description="Food:",
        )


        def _sync_food_options(*_):
            query = (food_search.value or "").strip().lower()
            filtered_foods = [item for item in foods if query in str(item).lower()]
            food.options = filtered_foods
            food.value = filtered_foods[0] if filtered_foods else None


        food_search.observe(_sync_food_options, names="value")
        _sync_food_options()

        meal_type = widgets.Dropdown(
            options=["Breakfast", "Lunch", "Dinner", "Snack"],
            description="Meal Type:",
        )

        qty = widgets.Dropdown(
            # only show decimal options that are multiples of 0.5, up to 10, using floor division and modulus to determine if it's a whole number or half
            options=[i // 2 if i % 2 == 0 else i / 2 for i in range(1, 21)],
            description="Quantity:", value=1.0,
        )

        # Serving size display
        serving_size_out = widgets.Output()
        
        submit = widgets.Button(description="Submit")
        out = widgets.Output()


        def _update_serving_size_display(*_):
            """Display the serving size for the selected food."""
            try:
                selected_food = food.value
                
                if not selected_food:
                    serving_size_out.clear_output()
                    return
                
                # For combos (starts with 'C'), query the view; for regular foods, query the food table
                if selected_food in views:
                    # It's a combo - query from the combo view
                    query = f"""
                        SELECT serving_size
                        FROM {selected_food}
                        LIMIT 1
                    """
                else:
                    # It's a regular food - query from food table
                    query = f"""
                        SELECT serving_size, measurement_unit
                        FROM food
                        WHERE name = '{selected_food}'
                    """
                
                df = run_select(query, return_df=True)
                
                if df.empty:
                    serving_size_out.clear_output(wait=True)
                    with serving_size_out:
                        display(HTML("<p style='color: orange; font-size: 12px;'>Serving size not available</p>"))
                    return
                
                # Get the serving size info
                row = df.iloc[0]
                serving_size = row.get('serving_size', 'N/A')
                measurement_unit = row.get('measurement_unit', '') if 'measurement_unit' in row else ''
                
                # Format the display
                if serving_size and serving_size != 'N/A':
                    serving_text = f"{serving_size} {measurement_unit}".strip()
                else:
                    serving_text = "N/A"
                
                serving_size_out.clear_output(wait=True)
                with serving_size_out:
                    display(HTML(f"""
                    <div style="background:rgb(20, 50, 80); color:rgb(180, 220, 255); padding:8px 12px; border-radius:5px; border-left:3px solid rgb(100, 200, 255); font-size:12px;">
                        <b>Serving Size:</b> {serving_text}
                    </div>
                    """))
            
            except Exception as e:
                serving_size_out.clear_output(wait=True)
                with serving_size_out:
                    display(HTML(f"<p style='color: red; font-size: 12px;'>Error: {str(e)}</p>"))

        def on_food_change(*_):
            """Update serving size when food selection changes."""
            _update_serving_size_display()

        # Observe food selection changes
        food.observe(on_food_change, names="value")
        _update_serving_size_display()  # Initial display


        def on_submit(_):
            try: 
                selected_food = food.value
                selected_meal_type = meal_type.value
                selected_qty = qty.value
                selected_log_date = (log_date.value if override_date.value else None)

                # Check for duplicate combo
                if selected_food in views:  # Only check for duplicates if the selected food is a combo
                        result_df = run_select(f"SELECT 1 FROM food_log  WHERE log_date = '{selected_log_date or date.today().isoformat()}' AND upper(meal_type) = '{selected_meal_type.upper()}' AND upper(combo_name) = '{selected_food[1:].upper()}' LIMIT 1",
                        return_df=True
                        )
                        
                        
                        if not result_df.empty:  # If a result was found
                            out.clear_output(wait=True)
                            with out:
                                display(HTML(f"""
                                <div style="background:rgb(200, 50, 50); color:white; padding:10px; width:80%; border-radius:9px;">
                                    <p><b>⚠️ Combo Already Logged</b></p>
                                    <p>You already logged <b>{selected_food}</b> for <b>{selected_meal_type}</b> on {(selected_log_date or date.today()).isoformat()}</p>
                                </div>
                                """))
                            
                            # Reset the widgets
                            food.value = all_foods[0] if all_foods else None
                            food_search.value = ""
                            qty.value = 1.0
                            
                            submit.disabled = False
                            return  # Exit early, don't insert   
                

                wt = WellnessTracker()

                wt.insert_food_log(
                        selected_food,
                        selected_meal_type,
                        selected_qty,
                        log_date=selected_log_date,
                    )

                out.clear_output(wait=True)

                with out:

                        display(
                            HTML(
                                f"""
                                <div style="
                                    background:rgb(1, 8, 15);
                                    color:teal;
                                    padding:10px;
                                    width:80%;
                                    border-radius:9px;
                                ">

                                <h2 style="background-color:rgb(210, 220, 230); color:rgb(20, 19, 25); margin-top:0;padding:5px;border-radius:5px;width:fit-content;">
                                    Submitted Successfully!
                                </h2>

                                <p><b>Date:</b> {(selected_log_date or date.today()).isoformat()}</p>

                                <p><b>Food:</b> {selected_food}</p>

                                <p><b>Meal Type:</b> {selected_meal_type}</p>

                                <p><b>Qty:</b> {selected_qty}</p>

                                </div>
                                """
                            )
                        )

                
            except Exception as e:
                    with out:
                        display(HTML("<br><b><div style='color: red;'>DATABASE ERROR:</b></div>"))
                        display(HTML(f"<div style='background: rgb(230, 230, 230); padding:3px;border-radius:5px;font-family: Courier;'>{str(e)}</div><br>"))
                        ai = OpenAIClient()
                        
                        # Prefer the snapshot values captured before try — fall back to live widget values
                        sf_raw = selected_food if 'selected_food' in locals() else food.value
                        sm_raw = selected_meal_type if 'selected_meal_type' in locals() else meal_type.value
                        sq_raw = selected_qty if 'selected_qty' in locals() else qty.value
                        sd_raw = selected_log_date if 'selected_log_date' in locals() else (log_date.value if override_date.value else None)
                        
                        # normalize to safe display strings
                        
                    display(HTML("<p style='background-color:rgb(22, 22, 22);width:100%;color:red;padding:5px;border-radius:5px;width:fit-content;'><b>Generating Error Explanation...</b></p>"))
                    # display(HTML("<br>"))
                    
                    def _s(x):
                            if x is None:
                                return "<None>"
                            try:
                                return x.isoformat() if hasattr(x, "isoformat") else str(x)
                            except Exception:
                                return "<unserializable>"

                    sf = _s(sf_raw)
                    sm = _s(sm_raw)
                    sq = _s(sq_raw)
                    sd = _s(sd_raw)
                    
                    
                    prompt = (
                                f"You are a concise assistant. Given the Python exception below, produce a concise explanation with the summary and likely cause on separate lines:\n"
                                f"- **Summary**: one sentence in plain English\n"
                                f"- **Likely cause**: one sentence\n\n"
                                f"Exception:\n{e}\n\n"
                                f"These are the actual values that were being processed when the error occurred:\n"
                                f"Food: {sf}\n"
                                f"Meal Type: {sm}\n"
                                f"Quantity: {sq}\n"
                                f"Log Date: {sd}\n\n"
                                "As the most common error will be duplicate entries, include the actual values in the error message to help the user understand what caused the error and how to fix it (e.g. by changing the date or quantity)."
                                "IMPORTANT UPDATE: Return your response in HTML format equivalent to the Markdown you'd normally use. Additionally, have the background color as rgb(22, 22, 22) and use a bit of padding as well."
                            )
                    ai_msg = ai.get_response(prompt)
                    display(HTML(f"<div style='background-color:rgb(22, 22, 22); padding:5px;border-radius:5px;width:fit-content;'>{ai_msg}</div>"))
                    display(HTML("<br>"))
                        
            finally:
                    submit.disabled = False


        # Prevent duplicate handlers on rerun
        submit._click_handlers.callbacks.clear()

        submit.on_click(on_submit)

        # Create a layout with input on the left and serving size display on the right
        food_with_serving = widgets.HBox([
            food,
            serving_size_out
        ], layout=widgets.Layout(width='100%'))

        # Combine all inputs vertically
        input_panel = widgets.VBox([
            override_date,
            log_date,
            food_search,
            food_with_serving,
            meal_type,
            qty,
            submit,
        ])

        display(
            input_panel,
            out,
        )

    def ui_insert_exercise(self):
        """
        Create the exercise logging UI with exercise type dropdown, exercise name dropdown,
        duration input, notes, and submit button.
        """

        rows, _ = run_select(
            """
            SELECT exercise_type, name
            FROM exercise
            ORDER BY exercise_type, name;
            """,
            return_df=False,
        )

        by_type: dict[str, list[str]] = {}
        for ex_type, ex_name in rows:
            by_type.setdefault(ex_type, []).append(ex_name)

        exercise_types = list(by_type.keys())
        initial_type = exercise_types[0] if exercise_types else None
        initial_names = by_type.get(initial_type, [])

        override_date = widgets.Checkbox(description="Override date", value=False)
        log_date = widgets.DatePicker(description="Log Date:", value=date.today())

        def _sync_date_visibility(*_):
            if override_date.value:
                log_date.layout.display = ""
                if log_date.value is None:
                    log_date.value = date.today()
            else:
                log_date.layout.display = "none"

        override_date.observe(_sync_date_visibility, names="value")
        _sync_date_visibility()

        exercise_type = widgets.Dropdown(
            options=exercise_types,
            value=initial_type,
            description="Type:",
        )

        exercise_name = widgets.Dropdown(
            options=initial_names,
            description="Exercise:",
        )

        def _sync_exercise_names(*_):
            t = exercise_type.value
            names = by_type.get(t, [])
            exercise_name.options = names
            exercise_name.value = names[0] if names else None

        exercise_type.observe(_sync_exercise_names, names="value")
        _sync_exercise_names()

        duration_minutes = widgets.BoundedIntText(
            value=5,
            min=1,
            max=1440,
            step=1,
            description="Minutes:",
        )

        notes = widgets.Textarea(
            value="",
            description="Notes:",
            layout=widgets.Layout(width="80%", height="80px"),
        )

        submit = widgets.Button(description="Submit")
        out = widgets.Output()

        def on_submit(_):
            submit.disabled = True
            try:
                selected_log_date = log_date.value if override_date.value else None

                self.wellness_tracker.insert_exercise_log(
                    exercise_type=exercise_type.value,
                    exercise_name=exercise_name.value,
                    duration_minutes=duration_minutes.value,
                    notes=notes.value or None,
                    log_date=selected_log_date,
                )

                out.clear_output(wait=True)
                with out:
                    display(
                        HTML(
                            f"""
                            <div style="
                                background:rgb(1, 8, 15);
                                color:teal;
                                padding:10px;
                                width:80%;
                                border-radius:9px;
                            ">
                              <h2 style="background-color:rgb(210, 220, 230); color:rgb(20, 19, 25); margin-top:0;padding:5px;border-radius:5px;width:fit-content;"
                              >Submitted Successfully</h2>
                              <p><b>Date:</b> {(selected_log_date or date.today()).isoformat()}</p>
                              <p><b>Type:</b> {exercise_type.value}</p>
                              <p><b>Exercise:</b> {exercise_name.value}</p>
                              <p><b>Minutes:</b> {duration_minutes.value}</p>
                            </div>
                            """
                        )
                    )

            except Exception as e:
                with out:
                    display(HTML("<br><b><div style='color: red;'>DATABASE ERROR:</b></div>"))
                    display(HTML(f"<div style='background: rgb(230, 230, 230); padding:3px;border-radius:5px;font-family: Courier;'>{str(e)}</div><br>"))
                    display(Markdown("**Generating Error Explanation...**"))
                    display(HTML("<br>"))
                    ai = self.openai_client
                    stype = locals().get("exercise_type", exercise_type.value)
                    sname = locals().get("exercise_name", exercise_name.value)
                    smins = locals().get("duration_minutes", duration_minutes.value)
                    snotes = locals().get("notes", notes.value or None)
                    sdate = locals().get("selected_log_date", (log_date.value if override_date.value else None))
                    prompt = (
                        f"You are a concise assistant. Given the Python exception below, produce a concise explanation with the summary and likely cause on separate lines:\n"
                        f"- **Summary**: one sentence in plain English\n"
                        f"- **Likely cause**: one sentence\n\n"
                        f"Exception:\n{e}\n\n"
                        f"These are the actual values that were being processed when the error occurred:\n"
                        f"Exercise Type: {stype}\n"
                        f"Exercise Name: {sname}\n"
                        f"Minutes: {smins}\n"
                        f"Notes: {snotes}\n"
                        f"Log Date: {sdate}\n\n"
                        "As the most common error will be duplicate entries, include the actual values in the error message to help the user understand what caused the error and how to fix it (e.g. by changing the date or minutes)."
                    )
                    ai_msg = ai.get_response(prompt)
                    display(Markdown(ai_msg))
                    display(HTML("<br>"))
            finally:
                submit.disabled = False

        submit._click_handlers.callbacks.clear()
        submit.on_click(on_submit)

        display(
            override_date,
            log_date,
            exercise_type,
            exercise_name,
            duration_minutes,
            notes,
            submit,
            out,
        )

    def ui_insert_activity(self):
        """
        Create the activity logging UI with activity search, activity dropdown, duration, notes, and submit.
        """

        rows, _ = run_select(
            """
            SELECT name
            FROM activity
            ORDER BY name;
            """,
            return_df=False,
        )

        activities = [r[0] for r in rows]

        override_date = widgets.Checkbox(description="Override date", value=False)
        log_date = widgets.DatePicker(description="Log Date:", value=date.today())

        def _sync_date_visibility(*_):
            if override_date.value:
                log_date.layout.display = ""
                if log_date.value is None:
                    log_date.value = date.today()
            else:
                log_date.layout.display = "none"

        override_date.observe(_sync_date_visibility, names="value")
        _sync_date_visibility()

        activity_search = widgets.Text(description="Search:", placeholder="Type to filter activities")
        activity_name = widgets.Dropdown(options=activities, description="Activity:")

        def _sync_activity_options(*_):
            query = (activity_search.value or "").strip().lower()
            filtered_activities = [item for item in activities if query in str(item).lower()]
            activity_name.options = filtered_activities
            activity_name.value = filtered_activities[0] if filtered_activities else None

        activity_search.observe(_sync_activity_options, names="value")
        _sync_activity_options()

        duration_minutes = widgets.BoundedIntText(
            value=10,
            min=1,
            max=1440,
            step=1,
            description="Minutes:",
        )

        notes = widgets.Textarea(
            value="",
            description="Notes:",
            layout=widgets.Layout(width="80%", height="80px"),
        )

        submit = widgets.Button(description="Submit")
        out = widgets.Output()

        def on_submit(_):
            submit.disabled = True
            try:
                selected_log_date = log_date.value if override_date.value else None
                self.wellness_tracker.insert_activity_log(
                    activity_name=activity_name.value,
                    duration_minutes=duration_minutes.value,
                    notes=notes.value or None,
                    log_date=selected_log_date,
                )

                out.clear_output(wait=True)
                with out:
                    display(
                        HTML(
                            f"""
                            <div style="
                                background:rgb(1, 8, 15);
                                color:teal;
                                padding:10px;
                                width:80%;
                                border-radius:9px;
                            ">
                              <h2 style="background:rgb(210, 220, 230); color:rgb(20, 19, 25); margin-top:0;padding:5px;border-radius:5px;width:fit-content;">Submitted Successfully</h2>
                              <p><b>Date:</b> {(selected_log_date or date.today()).isoformat()}</p>
                              <p><b>Activity:</b> {activity_name.value}</p>
                              <p><b>Minutes:</b> {duration_minutes.value}</p>
                              <p><b>Notes:</b> {notes.value or "None"}</p>
                            </div>
                            """
                        )
                    )

            except Exception as e:
                with out:
                    display(HTML("<br><b><div style='color: red;'>DATABASE ERROR:</b></div>"))
                    display(HTML(f"<div style='background: rgb(230, 230, 230); padding:3px;border-radius:5px;font-family: Courier;'>{str(e)}</div><br>"))
                    display(Markdown("**Generating Error Explanation...**"))
                    display(HTML("<br>"))
                    ai = self.openai_client
                    aname = locals().get("activity_name", activity_name.value)
                    amins = locals().get("duration_minutes", duration_minutes.value)
                    anotes = locals().get("notes", notes.value or None)
                    adate = locals().get("selected_log_date", (log_date.value if override_date.value else None))
                    prompt = (
                        f"You are a concise assistant. Given the Python exception below, produce a concise explanation with the summary and likely cause on separate lines:\n"
                        f"- **Summary**: one sentence in plain English\n"
                        f"- **Likely cause**: one sentence\n\n"
                        f"Exception:\n{e}\n\n"
                        f"These are the actual values that were being processed when the error occurred:\n"
                        f"Activity: {aname}\n"
                        f"Minutes: {amins}\n"
                        f"Notes: {anotes}\n"
                        f"Log Date: {adate}\n\n"
                        "As the most common error will be duplicate entries, include the actual values in the error message to help the user understand what caused the error and how to fix it (e.g. by changing the date or minutes)."
                    )
                    ai_msg = ai.get_response(prompt)
                    display(Markdown(ai_msg))
                    display(HTML("<br>"))
            finally:
                submit.disabled = False

        submit._click_handlers.callbacks.clear()
        submit.on_click(on_submit)

        display(
            override_date,
            log_date,
            activity_search,
            activity_name,
            duration_minutes,
            notes,
            submit,
            out,
        )

    def ui_insert_stress(self):
        """
        Create the stress logging UI with stress level dropdowns for work, family, health, and other categories,
        plus work productivity level.
        """

        # ----------------------------
        # Date handling
        # ----------------------------
        override_date = widgets.Checkbox(
            description="Override date",
            value=False,
        )

        log_date = widgets.DatePicker(
            description="Log Date:",
            value=date.today(),
        )

        def _sync_date_visibility(*_):
            if override_date.value:
                log_date.layout.display = ""
                if log_date.value is None:
                    log_date.value = date.today()
            else:
                log_date.layout.display = "none"

        override_date.observe(_sync_date_visibility, names="value")
        _sync_date_visibility()

        # ----------------------------
        # Stress widgets
        # ----------------------------
        level_options = [
            "Completely Stress-Free",
            "Very Low Stress",
            "Slightly Stressed",
            "Moderately Stressed",
            "Highly Stressed",
            "Very Stressed",
            "Extremely Stressed"
        ]

        work_options = level_options.copy()
        work_options.insert(0, "No Work")

        productivity_levels = [
            "Exceptionally Productive",
            "Highly Productive",
            "Moderately Productive",
            "Slightly Productive",
            "Unproductive",
            "Very Unproductive",
            "No Work"
        ]

        work_stress = widgets.Dropdown(
            options=work_options,
            value="Completely Stress-Free",
            description="Work Stress:",
        )

        work_productivity = widgets.Dropdown(
            options=productivity_levels,
            value="Exceptionally Productive",
            description="Work Productivity:",
        )

        family_stress = widgets.Dropdown(
            options=level_options,
            value="Completely Stress-Free",
            description="Family Stress:",
        )

        health_stress = widgets.Dropdown(
            options=level_options,
            value="Completely Stress-Free",
            description="Health Stress:",
        )

        other_stress = widgets.Dropdown(
            options=level_options,
            value="Completely Stress-Free",
            description="Other Stress:",
        )

        notes = widgets.Textarea(
            value="",
            description="Notes:",
            layout=widgets.Layout(width="80%", height="80px"),
        )

        submit = widgets.Button(description="Submit")
        out = widgets.Output()

        def on_submit(_):
            submit.disabled = True
            try:
                selected_log_date = log_date.value if override_date.value else None

                self.wellness_tracker.insert_stress_log(
                    work_stress_level=work_stress.value,
                    work_productivity_level=work_productivity.value,
                    family_stress_level=family_stress.value,
                    health_stress_level=health_stress.value,
                    other_stress_level=other_stress.value,
                    notes=notes.value or None,
                    log_date=selected_log_date,
                )

                out.clear_output(wait=True)
                with out:
                    display(
                        HTML(
                            f"""
                            <div style="
                                background:rgb(1, 8, 15);
                                color:teal;
                                padding:10px;
                                width:80%;
                                border-radius:9px;
                            ">
                              <h2 style="background:rgb(210, 220, 230); color:rgb(20, 19, 25); margin-top:0;padding:5px;border-radius:5px;width:fit-content;">Submitted Successfully</h2>
                              <p><b>Date:</b> {(selected_log_date or date.today()).isoformat()}</p>
                              <p><b>Work Stress:</b> {work_stress.value}</p>
                              <p><b>Work Productivity:</b> {work_productivity.value}</p>
                              <p><b>Family Stress:</b> {family_stress.value}</p>
                              <p><b>Health Stress:</b> {health_stress.value}</p>
                              <p><b>Other Stress:</b> {other_stress.value}</p>
                              <p><b>Notes:</b> {notes.value or "None"}</p>
                            </div>
                            """
                        )
                    )

            except Exception as e:
                with out:
                    display(HTML("<br><b><div style='color: red;'>DATABASE ERROR:</b></div>"))
                    display(HTML(f"<div style='background: rgb(230, 230, 230); padding:3px;border-radius:5px;font-family: Courier;'>{str(e)}</div><br>"))
                    display(Markdown("**Generating Error Explanation...**"))
                    display(HTML("<br>"))
                    ai = self.openai_client
                    w_stress = locals().get("work_stress_level", work_stress.value)
                    w_productivity = locals().get("work_productivity_level", work_productivity.value)
                    f_stress = locals().get("family_stress_level", family_stress.value)
                    h_stress = locals().get("health_stress_level", health_stress.value)
                    o_stress = locals().get("other_stress_level", other_stress.value)
                    notes_value = locals().get("notes", notes.value or None)
                    log_date_value = locals().get("selected_log_date", (log_date.value if override_date.value else None))
                    prompt = (
                        f"You are a concise assistant. Given the Python exception below, produce a concise explanation with the summary and likely cause on separate lines:\n"
                        f"- **Summary**: one sentence in plain English\n"
                        f"- **Likely cause**: one sentence\n\n"
                        f"Exception:\n{e}\n\n"
                        f"These are the actual values that were being processed when the error occurred:\n"
                        f"Work Stress: {w_stress}\n"
                        f"Work Productivity: {w_productivity}\n"
                        f"Family Stress: {f_stress}\n"
                        f"Health Stress: {h_stress}\n"
                        f"Other Stress: {o_stress}\n"
                        f"Notes: {notes_value}\n"
                        f"Log Date: {log_date_value}\n\n"
                        "As the most common error will be duplicate entries, include the actual values in the error message to help the user understand what caused the error and how to fix it (e.g. by changing the date or minutes)."
                    )
                    ai_msg = ai.get_response(prompt)
                    display(Markdown(ai_msg))
                    display(HTML("<br>"))

            finally:
                submit.disabled = False

        submit._click_handlers.callbacks.clear()
        submit.on_click(on_submit)

        display(
            override_date,
            log_date,
            work_stress,
            work_productivity,
            family_stress,
            health_stress,
            other_stress,
            notes,
            submit,
            out,
        )


    def insert_sleep_water_weather(self):
        # ----------------------------
        # Shared date handling
        # ----------------------------
        override_date = widgets.Checkbox(description="Override date", value=False)

        log_date = widgets.DatePicker(
            description="Log Date:",
            value=date.today(),
        )

        def _sync_date_visibility(*_):
            if override_date.value:
                log_date.layout.display = ""
                if log_date.value is None:
                    log_date.value = date.today()
            else:
                log_date.layout.display = "none"

        override_date.observe(_sync_date_visibility, names="value")
        _sync_date_visibility()

        def _selected_log_date():
            return log_date.value if override_date.value else None

        def _effective_log_date():
            return _selected_log_date() or date.today()

        # ----------------------------
        # Sleep tab (hour+minute only)
        # ----------------------------
        hours = [(f"{h:02d}", h) for h in range(0, 24)]
        minutes = [(f"{m:02d}", m) for m in range(0, 60, 5)]  # 5-min granularity; adjust if desired

        bed_hour = widgets.Dropdown(description="Bedtime Hour:", options=hours, value=0)
        bed_hour.tooltip = "Hour of bedtime"
        bed_min = widgets.Dropdown(description="Bedtime Min:", options=minutes, value=30)

        wake_hour = widgets.Dropdown(description="Wake Hour:", options=hours, value=7)
        wake_min = widgets.Dropdown(description="Wake Min:", options=minutes, value=30)

        interruptions = widgets.Dropdown(
            description="Interruptions:",
            options=[(str(i), i) for i in range(0, 21)],
            value=0,
        )

        total_interruption_minutes = widgets.BoundedIntText(
            description="Interrupt Minutes:",
            value=0,
            min=0,
            max=1440,
            step=1,
        )
        total_interruption_minutes.tooltip = "Total interruption minutes (sum of all brief awake periods)"

        sleep_notes = widgets.Textarea(
            value="",
            description="Notes:",
            layout=widgets.Layout(width="80%", height="80px"),
        )

        sleep_submit = widgets.Button(description="Submit Sleep")
        sleep_out = widgets.Output()


        def on_sleep_submit(_):
            sleep_submit.disabled = True
            try:
                d = _effective_log_date()

                bed_t = time(bed_hour.value, bed_min.value)
                wake_t = time(wake_hour.value, wake_min.value)

                bedtime_dt = datetime.combine(d, bed_t)

                # If wake time is "earlier" than bedtime, assume it’s next day
                wake_dt = datetime.combine(d, wake_t)
                if wake_dt <= bedtime_dt:
                    wake_dt = wake_dt + timedelta(days=1)
                
                
                wt = WellnessTracker()
                wt.insert_sleep_log(
                    bedtime=bedtime_dt,
                    wake_time=wake_dt,
                    interruptions=interruptions.value,
                    total_interruption_minutes=total_interruption_minutes.value,
                    notes= sleep_notes.value or None,
                    log_date=_selected_log_date(),
                )

                sleep_out.clear_output(wait=True)
                with sleep_out:
                    display(HTML(f"""
                    <div style="background:rgb(1, 8, 15); padding:10px; width:80%; border-radius:9px;color:teal;">
                    <h2 style="background:rgb(210, 220, 230); color:rgb(20, 19, 25); margin-top:0;padding:5px;border-radius:5px;width:fit-content;">Sleep Submitted Successfully</h2>
                    <p><b>Date:</b> {d.isoformat()}</p>
                    <p><b>Bed:</b> {bed_hour.value:02d}:{bed_min.value:02d}</p>
                    <p><b>Wake:</b> {wake_hour.value:02d}:{wake_min.value:02d}</p>
                    <p><b>Interruptions:</b> {interruptions.value}</p>
                    <p><b>Total Interruption Minutes:</b> {total_interruption_minutes.value if total_interruption_minutes.value is not None else 'None'}</p>
                    </div>
                    """))
            except Exception as e:
                with sleep_out:
                    display(HTML("<br><b><div style='color: red;'>DATABASE ERROR:</b></div>"))
                    display(HTML(f"<div style='background: rgb(230, 230, 230); padding:3px;border-radius:5px;font-family: Courier;'>{str(e)}</div><br>"))
                    
                display(Markdown("**Generating Error Explanation...**"))
                ai = OpenAIClient()

                s_bed = locals().get("bedtime_dt", bedtime_dt if 'bedtime_dt' in locals() else None)
                s_wake = locals().get("wake_dt", wake_dt if 'wake_dt' in locals() else None)
                s_interruptions = locals().get("interruptions", interruptions.value)
                s_total_interruption_minutes = locals().get("total_interruption_minutes", total_interruption_minutes.value if 'total_interruption_minutes' in locals() else None)
                s_notes = locals().get("sleep_notes", sleep_notes.value or None)
                s_date = locals().get("d", _selected_log_date())

                prompt = (
                        "You are a concise assistant. Given the Python exception below, produce a properly formatted concise error explanation.\n"
                        "- **Error Details**: concise description in plain English\n"
                        f"Exception:\n{e}\n\n"
                        "These are the actual values that were being processed when the error occurred:\n"
                        f"Bedtime: {s_bed}\n"
                        f"Wake Time: {s_wake}\n"
                        f"Interruptions: {s_interruptions}\n"
                        f"Total Interruption Minutes: {s_total_interruption_minutes}\n"
                        f"Notes: {s_notes}\n"
                        f"Log Date: {s_date}\n\n"
                        "Ideally, include the actual values in the error message to help the user understand what caused the error and how to fix it (e.g. by changing the date or times)."
                    )

                ai_msg = ai.get_response(prompt)
                display(Markdown(ai_msg))
                display(HTML("<br>"))
            finally:
                sleep_submit.disabled = False
                
                
        sleep_submit._click_handlers.callbacks.clear()
        sleep_submit.on_click(on_sleep_submit)

        sleep_box = widgets.VBox([
            widgets.HTML("<b>Sleep</b>"),
            widgets.HBox([bed_hour, bed_min]),
            widgets.HBox([wake_hour, wake_min]),
            interruptions,
            total_interruption_minutes,
            sleep_notes,
            sleep_submit,
            sleep_out,
        ])

        # ----------------------------
        # Water tab (unchanged)
        # ----------------------------
        water_total_oz = widgets.BoundedFloatText(
            description="Total oz:",
            value=0.0,
            min=0.0,
            max=1000.0,
            step=1.0,
        )

        water_submit = widgets.Button(description="Submit Water")
        water_out = widgets.Output()

        def on_water_submit(_):
            water_submit.disabled = True
            try:
                wt = WellnessTracker()
                wt.insert_water_log(
                    total_oz=water_total_oz.value,
                    log_date=_selected_log_date(),
                )

                water_out.clear_output(wait=True)
                with water_out:
                    display(HTML(f"""
                    <div style="background:rgb(1, 8, 15); padding:10px; width:80%; border-radius:9px;color:teal;">
                    <h2 style="background:rgb(210, 220, 230); color:rgb(20, 19, 25); margin-top:0;padding:5px;border-radius:5px;width:fit-content;">Water Submitted Successfully</h2>
                    <p><b>Date:</b> {_effective_log_date().isoformat()}</p>
                    <p><b>Total oz:</b> {water_total_oz.value}</p>
                    </div>
                    """))
            except Exception as e:
                with water_out:
                    display(Markdown(f"ERROR: {e}"))
            finally:
                water_submit.disabled = False

        water_submit._click_handlers.callbacks.clear()
        water_submit.on_click(on_water_submit)

        water_box = widgets.VBox([water_total_oz, water_submit, water_out])

        # ----------------------------
        # Weather tab (no precipitation; conditions dropdown)
        # ----------------------------
        temp_min_f = widgets.BoundedFloatText(description="Min Temp (F):", value=0.0, min=-100.0, max=150.0, step=1)
        temp_max_f = widgets.BoundedFloatText(description="Max Temp (F):", value=0.0, min=-100.0, max=150.0, step=1)

        humidity_level = widgets.Dropdown(
            description="Humidity:",
            options=[("Low", "Low"), ("Moderate", "Moderate"), ("High", "High")],
            value=None,
        )

        conditions = widgets.Dropdown(
            description="Conditions:",
            options=[
                ("Clear", "Clear"),
                ("Partly Cloudy", "Partly Cloudy"),
                ("Overcast", "Overcast"),
                ("Rain", "Rain"),
                ("Storm", "Storm"),
                ("Snow", "Snow"),
                ("Fog", "Fog"),
                ("Windy", "Windy"),
                ("Other", "Other"),
            ],
            value=None,
        )

        weather_notes = widgets.Textarea(
            value="",
            description="Notes:",
            layout=widgets.Layout(width="80%", height="80px"),
        )

        weather_submit = widgets.Button(description="Submit Weather")
        weather_out = widgets.Output()

        def on_weather_submit(_):
            weather_submit.disabled = True
            try:
                wt = WellnessTracker()
                wt.insert_weather_log(
                    temp_min_f=temp_min_f.value,
                    temp_max_f=temp_max_f.value,
                    humidity_level=humidity_level.value,
                    conditions=conditions.value,
                    notes=weather_notes.value or None,
                    log_date=_selected_log_date(),
                )

                weather_out.clear_output(wait=True)
                with weather_out:
                    display(HTML(f"""
                        <div style="background:rgb(1, 8, 15); padding:10px; width:80%; border-radius:9px;color:teal;">
                        <h2 style="background:rgb(210, 220, 230); color:rgb(20, 19, 25); margin-top:0;padding:5px;border-radius:5px;width:fit-content;">Weather Submitted Successfully</h2>
                        <p><b>Date:</b> {_effective_log_date().isoformat()}</p>
                        <p><b>Min Temp (F):</b> {temp_min_f.value}</p>
                        <p><b>Max Temp (F):</b> {temp_max_f.value}</p>
                        <p><b>Humidity:</b> {humidity_level.value or 'None'}</p>
                        <p><b>Conditions:</b> {conditions.value or 'None'}</p>
                        <p><b>Notes:</b> {weather_notes.value or 'None'}</p>
                        </div>
                        """))
            except Exception as e:
                with weather_out:
                    display(HTML("<br><b><div style='color: red;'>DATABASE ERROR:</b></div>"))
                    display(HTML(f"<div style='background: rgb(230, 230, 230); padding:3px;border-radius:5px;font-family: Courier;'>{str(e)}</div><br>"))
                    display(Markdown("**Generating Error Explanation...**"))
                    display(HTML("<br>"))

                    ai = OpenAIClient()

                    w_min = locals().get("temp_min_f", temp_min_f.value)
                    w_max = locals().get("temp_max_f", temp_max_f.value)
                    w_humidity = locals().get("humidity_level", humidity_level.value)
                    w_conditions = locals().get("conditions", conditions.value)
                    w_notes = locals().get("weather_notes", weather_notes.value or None)
                    w_date = locals().get("_selected_log_date", _selected_log_date())

                    prompt = (
                        "You are a concise assistant. Given the Python exception below, produce a properly formatted concise error explanation.\n"
                        "- **Error Details**: concise description in plain English\n"
                        
                        f"Exception:\n{e}\n\n"
                        "These are the actual values that were being processed when the error occurred:\n"
                        f"Min Temp (F): {w_min}\n"
                        f"Max Temp (F): {w_max}\n"
                        f"Humidity: {w_humidity}\n"
                        f"Conditions: {w_conditions}\n"
                        f"Notes: {w_notes}\n"
                        f"Log Date: {w_date}\n\n"
                        "Ideally, include the actual values in the error message to help the user understand what caused the error and how to fix it (e.g. by changing the date or values)."
                    )

                    ai_msg = ai.get_response(prompt)
                    display(Markdown(ai_msg))
                    display(HTML("<br>"))
            finally:
                weather_submit.disabled = False

        weather_submit._click_handlers.callbacks.clear()
        weather_submit.on_click(on_weather_submit)

        weather_box = widgets.VBox([
            temp_min_f,
            temp_max_f,
            humidity_level,
            conditions,
            weather_notes,
            weather_submit,
            weather_out,
        ])

        # ----------------------------
        # Hygiene tab (adds to same UI group)
        # ----------------------------
        hygiene_time_options = [
            ("—", None),
            ("Morning", "Morning"),
            ("Midday", "Midday"),
            ("Evening", "Evening"),
            ("Night", "Night"),
        ]

        brushed = widgets.Checkbox(description="Brushed Teeth:", value=False)
        brushed_time = widgets.Dropdown(description="Time of Day:", options=hygiene_time_options, value=None)

        flossed = widgets.Checkbox(description="Flossed:", value=False)
        flossed_time = widgets.Dropdown(description="Time of Day:", options=hygiene_time_options, value=None)

        showered = widgets.Checkbox(description="Showered:", value=False)
        shower_time = widgets.Dropdown(description="Time of Day:", options=hygiene_time_options, value=None)

        hygiene_notes = widgets.Textarea(value="", description="Notes:", layout=widgets.Layout(width="80%", height="80px"))
        hygiene_submit = widgets.Button(description="Submit Hygiene")
        hygiene_out = widgets.Output()

        # sync visibility + clear time when unchecked
        def _sync_hygiene_time_visibility(*_):
            brushed_time.layout.display = "" if brushed.value else "none"
            if not brushed.value:
                brushed_time.value = None

            flossed_time.layout.display = "" if flossed.value else "none"
            if not flossed.value:
                flossed_time.value = None

            shower_time.layout.display = "" if showered.value else "none"
            if not showered.value:
                shower_time.value = None

        brushed.observe(_sync_hygiene_time_visibility, names="value")
        flossed.observe(_sync_hygiene_time_visibility, names="value")
        showered.observe(_sync_hygiene_time_visibility, names="value")
        _sync_hygiene_time_visibility()

        def on_hygiene_submit(_):
            hygiene_submit.disabled = True
            try:
                wt = WellnessTracker()
                wt.insert_hygiene_log(
                    brushed=brushed.value,
                    flossed=flossed.value,
                    showered=showered.value,
                    brushed_time=brushed_time.value,
                    flossed_time=flossed_time.value,
                    shower_time=shower_time.value,
                    notes=hygiene_notes.value or None,
                    log_date=_selected_log_date(),
                )

                hygiene_out.clear_output(wait=True)
                with hygiene_out:
                    display(HTML(f"""
                    <div style="background:rgb(1, 8, 15); padding:10px; width:80%; border-radius:9px;color:teal;">
                    <h2 style="background:rgb(210, 220, 230); color:rgb(20, 19, 25); margin-top:0;padding:5px;border-radius:5px;width:fit-content;">Hygiene Submitted Successfully</h2>
                    <p><b>Date:</b> {_effective_log_date().isoformat()}</p>
                    <p><b>Brushed:</b> {brushed.value} {('('+ (brushed_time.value or '—') +')') if brushed_time.value else ''}</p>
                    <p><b>Flossed:</b> {flossed.value} {('('+ (flossed_time.value or '—') +')') if flossed_time.value else ''}</p>
                    <p><b>Showered:</b> {showered.value} {('('+ (shower_time.value or '—') +')') if shower_time.value else ''}</p>
                    <p><b>Notes:</b> {hygiene_notes.value or 'None'}</p>
                    </div>
                    """))
            except Exception as e:
                with hygiene_out:
                    display(HTML(f"<br><b><div style='color: red;'>DATABASE ERROR:</b></div>"))
                    display(HTML(f"<div style='background: rgb(230, 230, 230); padding:3px;border-radius:5px;font-family: Courier;'>{str(e)}</div><br>"))

                display(Markdown("**Generating Error Explanation...**"))
                display(HTML("<br>"))
                ai = OpenAIClient()

                # prefer the local selected_* values (fall back to widget values)
                b = locals().get("brushed", brushed.value)
                bt = locals().get("brushed_time", brushed_time.value)
                f = locals().get("flossed", flossed.value)
                ft = locals().get("flossed_time", flossed_time.value)
                s = locals().get("showered", showered.value)
                st = locals().get("shower_time", shower_time.value)
                notes_val = locals().get("hygiene_notes", hygiene_notes.value or None)
                sdate = locals().get("_selected_log_date", _selected_log_date())

                prompt = (
                    "You are a concise assistant. Given the Python exception below, produce a concise explanation with the summary and likely cause on separate lines:\n"
                    "- **Summary**: one sentence in plain English\n"
                    "- **Likely cause**: one sentence\n\n"
                    f"Exception:\n{e}\n\n"
                    "These are the actual values that were being processed when the error occurred:\n"
                    f"Brushed: {b}\n"
                    f"Brushed Time: {bt}\n"
                    f"Flossed: {f}\n"
                    f"Flossed Time: {ft}\n"
                    f"Showered: {s}\n"
                    f"Shower Time: {st}\n"
                    f"Notes: {notes_val}\n"
                    f"Log Date: {sdate}\n\n"
                    "As the most common error will be duplicate entries, include the actual values in the error message to help the user understand what caused the error and how to fix it (e.g. by changing the date or values)."
                )

                ai_msg = ai.get_response(prompt)
                display(Markdown(ai_msg))
                display(HTML("<br>"))
            finally:
                hygiene_submit.disabled = False

        hygiene_submit._click_handlers.callbacks.clear()
        hygiene_submit.on_click(on_hygiene_submit)

        hygiene_box = widgets.VBox([
            widgets.HTML("<b>Hygiene</b>"),
            widgets.HBox([brushed, brushed_time]),
            widgets.HBox([flossed, flossed_time]),
            widgets.HBox([showered, shower_time]),
            hygiene_notes,
            hygiene_submit,
            hygiene_out,
        ])


        # ----------------------------
        # Tabs wrapper
        # ----------------------------
        tabs = widgets.Tab(children=[sleep_box, water_box, weather_box, hygiene_box])
        tabs.set_title(0, "Sleep")
        tabs.set_title(1, "Water")
        tabs.set_title(2, "Weather")
        tabs.set_title(3, "Hygiene")

        display(override_date, log_date, tabs)

    def ui_insert_weight_waist(self):
        """
        Create a standalone UI for entering today's weight and waist measurements.
        This stays separate from the combined sleep/water/weather interface.
        """
        override_date = widgets.Checkbox(description="Override date", value=False)

        log_date = widgets.DatePicker(
            description="Log Date:",
            value=date.today(),
        )

        def _sync_date_visibility(*_):
            if override_date.value:
                log_date.layout.display = ""
                if log_date.value is None:
                    log_date.value = date.today()
            else:
                log_date.layout.display = "none"

        override_date.observe(_sync_date_visibility, names="value")
        _sync_date_visibility()

        def _selected_log_date():
            return log_date.value if override_date.value else None

        def _effective_log_date():
            return _selected_log_date() or date.today()

        weight_lbs = widgets.BoundedFloatText(
            description="Weight (lbs):",
            value=0.0,
            min=0.0,
            max=1000.0,
            step=0.1,
        )

        waist_inches = widgets.BoundedFloatText(
            description="Waist (in):",
            value=0.0,
            min=0.0,
            max=200.0,
            step=0.1,
        )

        submit = widgets.Button(description="Submit Measurements")
        out = widgets.Output()

        def on_submit(_):
            submit.disabled = True
            try:
                selected_log_date = _selected_log_date()
                selected_weight = weight_lbs.value if weight_lbs.value > 0 else None
                selected_waist = waist_inches.value if waist_inches.value > 0 else None

                wt = WellnessTracker()
                wt.insert_measurements_log(
                    log_date=selected_log_date,
                    weight_lbs=selected_weight,
                    waist_inches=selected_waist,
                )

                out.clear_output(wait=True)
                with out:
                    display(HTML(f"""
                    <div style="background:rgb(1, 8, 15); padding:10px; width:80%; border-radius:9px;color:teal;">
                    <h2 style="background:rgb(210, 220, 230); color:rgb(20, 19, 25); margin-top:0;padding:5px;border-radius:5px;width:fit-content;">Measurements Submitted Successfully</h2>
                    <p><b>Date:</b> {_effective_log_date().isoformat()}</p>
                    <p><b>Weight:</b> {selected_weight if selected_weight is not None else 'None'} lbs</p>
                    <p><b>Waist:</b> {selected_waist if selected_waist is not None else 'None'} in</p>
                    </div>
                    """))
            except Exception as e:
                with out:
                    display(HTML("<br><b><div style='color: red;'>DATABASE ERROR:</b></div>"))
                    display(HTML(f"<div style='background: rgb(230, 230, 230); padding:3px;border-radius:5px;font-family: Courier;'>{str(e)}</div><br>"))

                display(Markdown("**Generating Error Explanation...**"))
                display(HTML("<br>"))

                ai = self.openai_client
                w_weight = locals().get("selected_weight", weight_lbs.value if weight_lbs.value > 0 else None)
                w_waist = locals().get("selected_waist", waist_inches.value if waist_inches.value > 0 else None)
                w_log_date = locals().get("selected_log_date", _selected_log_date())

                prompt = (
                    "You are a concise assistant. Given the Python exception below, produce a concise explanation with the summary and likely cause on separate lines:\n"
                    "- **Summary**: one sentence in plain English\n"
                    "- **Likely cause**: one sentence\n\n"
                    f"Exception:\n{e}\n\n"
                    "These are the actual values that were being processed when the error occurred:\n"
                    f"Weight (lbs): {w_weight}\n"
                    f"Waist (in): {w_waist}\n"
                    f"Log Date: {w_log_date}\n\n"
                    "As the most common error will be duplicate entries, include the actual values in the error message to help the user understand what caused the error and how to fix it (e.g. by changing the date or values)."
                )

                ai_msg = ai.get_response(prompt)
                display(Markdown(ai_msg))
                display(HTML("<br>"))
            finally:
                submit.disabled = False

        submit._click_handlers.callbacks.clear()
        submit.on_click(on_submit)

        display(
            override_date,
            log_date,
            weight_lbs,
            waist_inches,
            submit,
            out,
        )


if __name__ == "__main__":
    u = UIFunctions()
    u.get_view_combo_names()
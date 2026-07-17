import ipywidgets as widgets
from IPython.display import display, HTML, Markdown
from datetime import date
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
        views = run_select(query, return_df=True)['viewname'].tolist()
        
        # create one SQL query that unions all the distinct combo_names from each view
        union_sql = " UNION ".join(
        f"SELECT DISTINCT combo_name AS name FROM {view}"
        for view in views
        )
        
        df = run_select(union_sql, return_df=True)
        all_combo_names = df['name'].tolist()
        return all_combo_names
    
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


        submit = widgets.Button(description="Submit")
        out = widgets.Output()


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

        display(
            override_date,
            log_date,
            food_search,
            food,
            meal_type,
            qty,
            submit,
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
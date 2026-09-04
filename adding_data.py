import ipywidgets as widgets
from IPython.display import clear_output, display, HTML, Markdown
from AI import OpenAIClient
from postgres import run_select
from wellness_tracker import WellnessTracker


class AddFoodCombo:
    

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
        
        try:
            views = run_select(query, return_df=True,show_errors=True)['viewname'].tolist()
            # create one SQL query that unions all the distinct combo_names from each view
            union_sql = " UNION ".join(
            f"SELECT DISTINCT combo_name AS name FROM {view}"
            for view in views
            )
            
            df = run_select(union_sql, return_df=True,show_errors=False)
            all_combo_names = df['name'].tolist()
            return all_combo_names
        except Exception as e:
            return []

    def build_widget_data(self):
        """
        This function builds the widget data for the food dropdown widget. It retrieves the combo names of the views and constructs a list of 
        tuples containing the combo name and its corresponding value. The first tuple is a placeholder for the dropdown widget.
        """
        all_foods = []
        all_foods.extend(self.get_view_combo_names()) 
        all_foods.extend(run_select("select name from food order by name;", return_df=True)['name'].tolist())
        self.foods = all_foods

        self.combo_name = widgets.Text(value="", description="Combo Name:", placeholder="Enter name")
        self.food_search = widgets.Text(description="Search:", placeholder="Type to filter foods")
        self.food = widgets.Dropdown(options=self.foods, description="Food:")
        self.serving_amt = widgets.Dropdown(options=[i // 2 if i % 2 == 0 else i / 2 for i in range(1, 21)], description="Serving Size:", value=1.0)

        self.add_food = widgets.Button(description="Add Food")
        self.remove_last_food = widgets.Button(description="Remove Last Food")
        self.submit = widgets.Button(description="Submit Food Combo", button_style="success")
        self.out = widgets.Output()

        self.sfood_list = []
        self.serving_size_list = []
        self.wt = WellnessTracker()
    
    
    def _sync_food_options(self,*_):
        q = (self.food_search.value or "").strip().lower()
        filtered = [item for item in self.foods if q in str(item).lower()]
        self.food.options = filtered
        self.food.value = filtered[0] if filtered else None
    
    
    def on_add_food_clicked(self, _):

    # check if added food is a duplicate
        if self.sfood_list.count(self.food.value) > 0:
            with self.out:
                display(Markdown(f"Duplicate Food: {self.food.value} has already been added."))
            return  # <- return early to avoid duplicate messages / further handling
        
        # for proper submissions 
        if len(self.sfood_list) < 10:
            self.sfood_list.append(self.food.value)
            self.serving_size_list.append(self.serving_amt.value)

            with self.out:
                display(Markdown(f"**Food Added:** {self.food.value} — {self.serving_amt.value} serving(s)\n<br>"))   
                
        else:
                with self.out:
                    display(Markdown("Maximum of 10 foods allowed. Remove a food or submit the Combo as is."))
    
    def on_remove_last_food_clicked(self, _):
        if not self.sfood_list:
            with self.out:
                display(Markdown("No foods to remove."))
            return
        removed_food = self.sfood_list.pop()
        if self.serving_size_list:
            removed_amt = self.serving_size_list.pop()
        with self.out:
            display(HTML(
                f"<span style='color:#cc0000;line-height:1.5;'><b>Removed:</b> "
                f"{removed_food} — {removed_amt if 'removed_amt' in locals() else '?'}</span>"
                        ))
    
    
    def on_submit(self, _):
    
        # check if combo has at least two foods
        if len(self.sfood_list) < 2:
            with self.out:
                display(HTML("<br><b><div style='color: red;'>Food Combos need at least two foods.</div></b><br>"))
            return
        if self.combo_name.value.strip() == "":
            with self.out:
                display(HTML("<br><b><div style='color: red;'>Please provide a name for the Food Combo.</div></b><br>"))
            return
        self.submit.disabled = True
        try:
            self.wt.create_combo_view(self.combo_name.value, self.sfood_list, self.serving_size_list)
            self.out.clear_output(wait=True)
            items_html = "".join(f"<li>{f} — {q}</li>" for f, q in zip(self.sfood_list, self.serving_size_list))
            with self.out:
                display(HTML(f"""
                    <div style="background:rgb(1,8,15);color:teal;padding:10px;border-radius:9px;width:80%;">
                    <h2 style="background-color:rgb(210,220,230);color:rgb(20,19,25);margin-top:0;padding:5px;border-radius:5px;width:fit-content;">
                        Combo Created
                    </h2>
                    <p><b>Name:</b> {self.combo_name.value}</p>
                    <ul style="margin:0;padding-left:1.2em;">{items_html}</ul>
                    </div>
                """))
                # clear the lists to allow for submitting another view
                self.sfood_list.clear()
                self.serving_size_list.clear()
                # clear widget values
                self.combo_name.value = ""
                self.serving_amt.value = 1
        except Exception as e:
            self.out.clear_output(wait=True)
            with self.out:
                display(HTML("<br><b><div style='color: red;'>DATABASE ERROR:</b></div>"))
                display(HTML(f"<div style='background: rgb(230, 230, 230); padding:3px;border-radius:5px;font-family: Courier;'>{str(e)}</div><br>"))
            ai = OpenAIClient()
            sf = self.combo_name.value
            sf_items = ", ".join(f"{f} ({q})" for f, q in zip(self.sfood_list, self.serving_size_list)) or "<None>"
            prompt = (f"Explain concisely why creating this combo failed.\nCombo name: {sf}\nItems: {sf_items}\n\nException:\n{e}")
            ai_msg = ai.get_response(prompt)
            with self.out:
                display(HTML(f"<div style='background-color:rgb(22, 22, 22); padding:5px;border-radius:5px;width:fit-content;color:#fff;'>{ai_msg}</div>"))
        finally:
            self.submit.disabled = False


    
    def run(self):
        self.build_widget_data()

        self.food_search.observe(self._sync_food_options, names="value")
        self.add_food.on_click(self.on_add_food_clicked)
        self.remove_last_food.on_click(self.on_remove_last_food_clicked)
        self.submit.on_click(self.on_submit)

        self._sync_food_options()

        self.ui = widgets.VBox(
    [
        self.combo_name,
        self.food_search,
        self.food,
        self.serving_amt,
        widgets.HBox([
            self.add_food,
            self.remove_last_food,
        ]),
        self.submit,
        widgets.Box(layout=widgets.Layout(height="8px")),
        self.out
    ],
    layout=widgets.Layout(
        padding="0 0 15px 0"
    )
)

        display(self.ui)





class AddNewFood:
    """
    UI for adding and updating foods in the wellness tracker.
    """

    def __init__(self, tracker=None):
        # ---------------------------------------------------------
        # Tracker
        # ---------------------------------------------------------
        self.wt = tracker or WellnessTracker()

        # ---------------------------------------------------------
        # Inject CSS
        # ---------------------------------------------------------
        self._inject_css()

        # ---------------------------------------------------------
        # Input widgets
        # ---------------------------------------------------------
        self.name_input = widgets.Text(
            description="Food Name:",
            value=""
        )

        self.calories_input = widgets.FloatText(
            description="Calories:",
            value=None
        )

        self.carbs_input = widgets.FloatText(
            description="Carbs:",
            value=None
        )

        self.proteins_input = widgets.FloatText(
            description="Protein:",
            value=None
        )

        self.fats_input = widgets.FloatText(
            description="Fats:",
            value=None
        )

        self.fiber_input = widgets.FloatText(
            description="Fiber:",
            value=None
        )

        self.serving_input = widgets.FloatText(
            description="Serving Size:",
            value=None
        )

        self.unit_input = widgets.Text(
            description="Unit:",
            value=""
        )

        # ---------------------------------------------------------
        # Buttons
        # ---------------------------------------------------------
        self.submit_food = widgets.Button(
            description="Add Food",
            button_style="success"
        )

        self.confirm_update = widgets.Button(
            description="Update Existing",
            button_style="warning"
        )

        self.cancel_update = widgets.Button(
            description="Cancel"
        )

        # ---------------------------------------------------------
        # Output
        # ---------------------------------------------------------
        self.food_out = widgets.Output()

        # ---------------------------------------------------------
        # Confirmation box
        # ---------------------------------------------------------
        self.confirm_box = widgets.HBox([
            self.confirm_update,
            self.cancel_update
        ])

        self.confirm_box.layout.display = "none"

        # ---------------------------------------------------------
        # Main container
        # ---------------------------------------------------------
        self.ui_box = widgets.VBox([
            self.name_input,
            self.calories_input,
            self.carbs_input,
            self.proteins_input,
            self.fats_input,
            self.fiber_input,
            self.serving_input,
            self.unit_input,
            self.submit_food,
            self.confirm_box,
            self.food_out
        ])

        self.ui_box.add_class("food-widget-box")

        # ---------------------------------------------------------
        # Attach handlers
        # ---------------------------------------------------------
        self._attach_handlers()

    # =============================================================
    # CSS
    # =============================================================

    def _inject_css(self):
        display(HTML("""
        <style>

        /* =========================================================
           Entire widget container
           ========================================================= */

        .food-widget-box {
            background-color: rgb(1, 8, 35);
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 8px;
        }

        /* =========================================================
           Labels
           ========================================================= */

        .food-widget-box label.widget-label {
            font-weight: bold;
            color: rgb(190, 190, 190);
            font-size: 14px;
        }

        /* =========================================================
           Input boxes
           ========================================================= */

        .food-widget-box input,
        .food-widget-box textarea,
        .food-widget-box select {
            background-color: rgb(160, 170, 190) !important;
            border: 1px solid #99ccff !important;
            border-radius: 4px;
            color: rgb(1, 8, 15) !important;
            font-size: 13px;
        }

        /* =========================================================
           Focused inputs
           ========================================================= */

        .food-widget-box input:focus,
        .food-widget-box textarea:focus,
        .food-widget-box select:focus {
            border-color: #3366cc !important;
            box-shadow: 0 0 4px #3366cc !important;
            outline: none !important;
        }

        /* =========================================================
           Buttons
           ========================================================= */

        .food-widget-box button {
            color: #ffffff !important;
            background-color: #006699 !important;
            border: 1px solid #004466 !important;
        }

        .food-widget-box button:hover {
            background-color: #0088cc !important;
        }

        </style>
        """))

    # =============================================================
    # Event handlers
    # =============================================================

    def _attach_handlers(self):

        # Clear existing handlers in case the widget gets rebuilt
        self.submit_food._click_handlers.callbacks.clear()
        self.confirm_update._click_handlers.callbacks.clear()
        self.cancel_update._click_handlers.callbacks.clear()

        self.submit_food.on_click(self._on_submit_food)
        self.confirm_update.on_click(self._on_confirm_update)
        self.cancel_update.on_click(self._on_cancel_update)

    # =============================================================
    # Save food
    # =============================================================

    def _save_food(self, update=False):

        name = self.name_input.value.strip()

        affected = self.wt.insert_new_food(
            name,
            self.calories_input.value,
            self.carbs_input.value,
            self.proteins_input.value,
            self.fats_input.value,
            self.fiber_input.value,
            self.serving_input.value,
            self.unit_input.value,
        )

        message = "updated" if update else "saved"

        self.confirm_box.layout.display = "none"

        with self.food_out:
            self.food_out.clear_output()
            
            if message == "updated":
                display(
                    HTML(
                        f"<br><div style='color:green'><b>{name} {message}</b> — {affected} row updated in the food database.</div>"
                    )
                )
            else:
                display(
                    HTML(
                        f"<br><div style='color:green'><b>{name} {message}</b> — {affected} row added to the food database.</div>"
                    )
                )

    # =============================================================
    # Submit
    # =============================================================

    def _on_submit_food(self, _):

        self.submit_food.disabled = True

        with self.food_out:
            self.food_out.clear_output()

        try:

            name = (self.name_input.value or "").strip()

            # -----------------------------------------------------
            # Food name
            # -----------------------------------------------------

            if not name:

                with self.food_out:
                    display(
                        HTML(
                            "<div style='color:red'>"
                            "Food name is required."
                            "</div>"
                        )
                    )

                return

            # -----------------------------------------------------
            # Required numeric fields
            # -----------------------------------------------------

            required_fields = [
                ("Calories", self.calories_input.value, True),
                ("Carbs", self.carbs_input.value, False),
                ("Protein", self.proteins_input.value, False),
                ("Fats", self.fats_input.value, False),
                ("Fiber", self.fiber_input.value, False),
                ("Serving Size", self.serving_input.value, True),
            ]

            for field_name, value, must_be_positive in required_fields:

                if value is None:

                    with self.food_out:
                        display(
                            HTML(
                                f"<div style='color:red'><b>"
                                f"{field_name} is required."
                                f"</b></div>"
                            )
                        )

                    return

                if must_be_positive and value <= 0:

                    with self.food_out:
                        display(
                            HTML(
                                f"<div style='color:red'><b>"
                                f"{field_name} must be greater than 0."
                                f"</b></div>"
                            )
                        )

                    return

                if not must_be_positive and value < 0:

                    with self.food_out:
                        display(
                            HTML(
                                f"<div style='color:red'><b>"
                                f"{field_name} cannot be negative."
                                f"</b></div>"
                            )
                        )

                    return

            # -----------------------------------------------------
            # Unit
            # -----------------------------------------------------

            if not (self.unit_input.value or "").strip():

                with self.food_out:
                    display(
                        HTML(
                            "<div style='color:red'><b>"
                            "Measurement unit is required."
                            "</b></div>"
                        )
                    )

                return

            # -----------------------------------------------------
            # Check if food already exists
            # -----------------------------------------------------

            safe_name = name.replace("'", "''")

            query = f"""
            SELECT food_id
            FROM food
            WHERE lower(name)=lower('{safe_name}')
            LIMIT 1;
            """

            rows, _ = run_select(query, return_df=False)

            if rows:

                with self.food_out:
                    display(
                        HTML(
                            f"""
                            <div style='color:red'>
                                <b>{name}</b> already exists.
                            </div>

                            <div style='margin-top:5px'>
                                Do you want to replace the existing values?
                            </div>
                            """
                        )
                    )

                self.confirm_box.layout.display = ""

                return

            # -----------------------------------------------------
            # Save new food
            # -----------------------------------------------------

            self._save_food(update=False)

        except Exception as e:

            with self.food_out:
                display(
                    HTML(
                        f"<div style='color:red'>{str(e)}</div>"
                    )
                )

        finally:

            self.submit_food.disabled = False

    # =============================================================
    # Confirm update
    # =============================================================

    def _on_confirm_update(self, _):
        self._save_food(update=True)

    # =============================================================
    # Cancel update
    # =============================================================

    def _on_cancel_update(self, _):

        self.confirm_box.layout.display = "none"

        with self.food_out:
            self.food_out.clear_output()

            display(
                HTML(
                    "<div style='color:gray'>"
                    "Update canceled."
                    "</div>"
                )
            )

    # =============================================================
    # Display widget
    # =============================================================

    def display(self):
        display(self.ui_box)

class AddNewExercise:
    """
    UI for adding and updating exercises in the wellness tracker.
    Allowed exercise types are limited to Cardio, Strength, and Balance.
    """

    ALLOWED_TYPES = ["Cardio", "Strength", "Mobility", "Physical Therapy", "Balance"]

    def __init__(self, tracker=None):
        self.wt = tracker or WellnessTracker()
        self._inject_css()

        self.exercise_name_input = widgets.Text(
            description="Exercise Name:",
            value="",
            style={"description_width": "100px"},
            layout=widgets.Layout(width="340px", margin="0 0 0 10px")
        )

        self.exercise_type_input = widgets.Dropdown(
            options=self.ALLOWED_TYPES,
            value="Cardio",
            description="Exercise Type:",
            style={"description_width": "100px"},
            layout=widgets.Layout(width="340px", margin="0 0 0 10px")
        )

        self.submit_exercise = widgets.Button(
            description="Add Exercise",
            button_style="success"
        )

        self.submit_container = widgets.HBox(
            [self.submit_exercise],
            layout=widgets.Layout(
                justify_content="flex-start",
                margin="12px 0 0 30px"
            )
        )

        self.confirm_update = widgets.Button(
            description="Update Existing",
            button_style="warning"
        )

        self.cancel_update = widgets.Button(
            description="Cancel"
        )

        self.exercise_out = widgets.Output()

        self.confirm_box = widgets.HBox([
            self.confirm_update,
            self.cancel_update
        ])

        self.confirm_box.layout.display = "none"

        self.ui_box = widgets.VBox([
            self.exercise_name_input,
            self.exercise_type_input,
            self.submit_container,
            self.confirm_box,
            self.exercise_out,
        ])

        self.ui_box.add_class("exercise-widget-box")
        self._attach_handlers()

    def _inject_css(self):
        display(HTML("""
        <style>
        .exercise-widget-box {
            background-color: rgb(1, 8, 35);
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 8px;
        }

        .exercise-widget-box label.widget-label {
            font-weight: bold;
            color: rgb(190, 190, 190);
            font-size: 14px;
        }

        .exercise-widget-box input,
        .exercise-widget-box textarea,
        .exercise-widget-box select {
            background-color: rgb(160, 170, 190) !important;
            border: 1px solid #99ccff !important;
            border-radius: 4px;
            color: rgb(1, 8, 15) !important;
            font-size: 13px;
        }

        .exercise-widget-box input:focus,
        .exercise-widget-box textarea:focus,
        .exercise-widget-box select:focus {
            border-color: #3366cc !important;
            box-shadow: 0 0 4px #3366cc !important;
            outline: none !important;
        }

        .exercise-widget-box button {
            color: #ffffff !important;
            background-color: #006699 !important;
            border: 1px solid #004466 !important;
        }

        .exercise-widget-box button:hover {
            background-color: #0088cc !important;
        }
        </style>
        """))

    def _attach_handlers(self):
        self.submit_exercise._click_handlers.callbacks.clear()
        self.confirm_update._click_handlers.callbacks.clear()
        self.cancel_update._click_handlers.callbacks.clear()

        self.submit_exercise.on_click(self._on_submit_exercise)
        self.confirm_update.on_click(self._on_confirm_update)
        self.cancel_update.on_click(self._on_cancel_update)

    def _save_exercise(self, update=False):
        name = self.exercise_name_input.value.strip()
        exercise_type = self.exercise_type_input.value.strip()

        affected = self.wt.insert_new_exercise(
            exercise_type=exercise_type,
            name=name,
        )

        message = "updated" if update else "saved"
        self.confirm_box.layout.display = "none"

        with self.exercise_out:
            self.exercise_out.clear_output()

            if message == "updated":
                display(
                    HTML(
                        f"<br><div style='color:green'><b>{name} {message}</b> — {affected} row updated in the exercise database.</div>"
                    )
                )
            else:
                display(
                    HTML(
                        f"<br><div style='color:green'><b>{name} {message}</b> — {affected} row added to the exercise database.</div>"
                    )
                )

    def _on_submit_exercise(self, _):
        self.submit_exercise.disabled = True

        with self.exercise_out:
            self.exercise_out.clear_output()

        try:
            name = (self.exercise_name_input.value or "").strip()
            exercise_type = (self.exercise_type_input.value or "").strip()

            if not name:
                with self.exercise_out:
                    display(
                        HTML(
                            "<div style='color:red'>"
                            "Exercise name is required."
                            "</div>"
                        )
                    )
                return

            normalized_type = {
                "cardio": "Cardio",
                "strength": "Strength",
                "balance": "Balance",
            }.get(exercise_type.lower(), exercise_type)

            if normalized_type not in self.ALLOWED_TYPES:
                with self.exercise_out:
                    display(
                        HTML(
                            "<div style='color:red'><b>"
                            "Exercise type must be one of: Cardio, Strength, Balance."
                            "</b></div>"
                        )
                    )
                return

            self.exercise_type_input.value = normalized_type

            safe_name = name.replace("'", "''")
            safe_type = normalized_type.replace("'", "''")

            query = f"""
            SELECT exercise_id
            FROM exercise
            WHERE lower(exercise_type) = lower('{safe_type}')
              AND lower(name) = lower('{safe_name}')
            LIMIT 1;
            """

            rows, _ = run_select(query, return_df=False)

            if rows:
                with self.exercise_out:
                    display(
                        HTML(
                            f"""
                            <div style='color:red'>
                                <b>{name}</b> already exists under the <b>{normalized_type}</b> type.
                            </div>
                            <div style='margin-top:5px'>
                                Do you want to replace the existing values?
                            </div>
                            """
                        )
                    )
                self.confirm_box.layout.display = ""
                return

            self._save_exercise(update=False)

        except Exception as e:
            with self.exercise_out:
                display(
                    HTML(
                        f"<div style='color:red'>{str(e)}</div>"
                    )
                )

        finally:
            self.submit_exercise.disabled = False

    def _on_confirm_update(self, _):
        self._save_exercise(update=True)

    def _on_cancel_update(self, _):
        self.confirm_box.layout.display = "none"

        with self.exercise_out:
            self.exercise_out.clear_output()
            display(
                HTML(
                    "<div style='color:gray'>"
                    "Update canceled."
                    "</div>"
                )
            )

    def display(self):
        display(self.ui_box)

class AddNewActivity:
    """
    UI for adding and updating activities in the wellness tracker.
    Activity has only one field: the activity name.
    """

    def __init__(self, tracker=None):
        self.wt = tracker or WellnessTracker()
        self._inject_css()

        self.activity_name_input = widgets.Text(
            description="Activity Name:",
            value="",
            style={"description_width": "120px"},
            layout=widgets.Layout(width="340px", margin="0 0 0 10px")
        )

        self.submit_activity = widgets.Button(
            description="Add Activity",
            button_style="success"
        )

        self.submit_container = widgets.HBox(
            [self.submit_activity],
            layout=widgets.Layout(
                justify_content="flex-start",
                margin="12px 0 0 30px"
            )
        )

        self.confirm_update = widgets.Button(
            description="Update Existing",
            button_style="warning"
        )

        self.cancel_update = widgets.Button(
            description="Cancel"
        )

        self.activity_out = widgets.Output()

        self.confirm_box = widgets.HBox([
            self.confirm_update,
            self.cancel_update
        ])

        self.confirm_box.layout.display = "none"

        self.ui_box = widgets.VBox([
            self.activity_name_input,
            self.submit_container,
            self.confirm_box,
            self.activity_out,
        ])

        self.ui_box.add_class("activity-widget-box")
        self._attach_handlers()

    def _inject_css(self):
        display(HTML("""
        <style>
        .activity-widget-box {
            background-color: rgb(1, 8, 35);
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 8px;
        }

        .activity-widget-box label.widget-label {
            font-weight: bold;
            color: rgb(190, 190, 190);
            font-size: 14px;
        }

        .activity-widget-box input,
        .activity-widget-box textarea,
        .activity-widget-box select {
            background-color: rgb(160, 170, 190) !important;
            border: 1px solid #99ccff !important;
            border-radius: 4px;
            color: rgb(1, 8, 15) !important;
            font-size: 13px;
        }

        .activity-widget-box input:focus,
        .activity-widget-box textarea:focus,
        .activity-widget-box select:focus {
            border-color: #3366cc !important;
            box-shadow: 0 0 4px #3366cc !important;
            outline: none !important;
        }

        .activity-widget-box button {
            color: #ffffff !important;
            background-color: #006699 !important;
            border: 1px solid #004466 !important;
        }

        .activity-widget-box button:hover {
            background-color: #0088cc !important;
        }
        </style>
        """))

    def _attach_handlers(self):
        self.submit_activity._click_handlers.callbacks.clear()
        self.confirm_update._click_handlers.callbacks.clear()
        self.cancel_update._click_handlers.callbacks.clear()

        self.submit_activity.on_click(self._on_submit_activity)
        self.confirm_update.on_click(self._on_confirm_update)
        self.cancel_update.on_click(self._on_cancel_update)

    def _save_activity(self, update=False):
        name = self.activity_name_input.value.strip()

        affected = self.wt.insert_new_activity(name=name)

        message = "updated" if update else "saved"
        self.confirm_box.layout.display = "none"

        with self.activity_out:
            self.activity_out.clear_output()

            if message == "updated":
                display(
                    HTML(
                        f"<br><div style='color:green'><b>{name} {message}</b> — {affected} row updated in the activity database.</div>"
                    )
                )
            else:
                display(
                    HTML(
                        f"<br><div style='color:green'><b>{name} {message}</b> — {affected} row added to the activity database.</div>"
                    )
                )

    def _on_submit_activity(self, _):
        self.submit_activity.disabled = True

        with self.activity_out:
            self.activity_out.clear_output()

        try:
            name = (self.activity_name_input.value or "").strip()

            if not name:
                with self.activity_out:
                    display(
                        HTML(
                            "<div style='color:red'>"
                            "Activity name is required."
                            "</div>"
                        )
                    )
                return

            safe_name = name.replace("'", "''")
            query = f"""
            SELECT activity_id
            FROM activity
            WHERE lower(name) = lower('{safe_name}')
            LIMIT 1;
            """

            rows, _ = run_select(query, return_df=False)

            if rows:
                with self.activity_out:
                    display(
                        HTML(
                            f"""
                            <div style='color:red'>
                                <b>{name}</b> already exists.
                            </div>
                            <div style='margin-top:5px'>
                                Do you want to replace the existing values?
                            </div>
                            """
                        )
                    )
                self.confirm_box.layout.display = ""
                return

            self._save_activity(update=False)

        except Exception as e:
            with self.activity_out:
                display(
                    HTML(
                        f"<div style='color:red'>{str(e)}</div>"
                    )
                )

        finally:
            self.submit_activity.disabled = False

    def _on_confirm_update(self, _):
        self._save_activity(update=True)

    def _on_cancel_update(self, _):
        self.confirm_box.layout.display = "none"

        with self.activity_out:
            self.activity_out.clear_output()
            display(
                HTML(
                    "<div style='color:gray'>"
                    "Update canceled."
                    "</div>"
                )
            )

    def display(self):
        display(self.ui_box)
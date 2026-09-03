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
        
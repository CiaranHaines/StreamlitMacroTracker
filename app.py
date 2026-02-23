import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import database as db
from parser import parse_gemini_table

# --- Initialization ---
st.set_page_config(page_title="Macro Tracker", page_icon="🍏", layout="wide")
db.init_db()

# --- Utility ---
def calculate_totals(df):
    if df.empty:
        return {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'fiber': 0}
    return df[['calories', 'protein', 'fat', 'carbs', 'fiber']].sum().to_dict()

# --- UI Setup ---
st.title("🍏 Macro Tracker")

tab_log, tab_dash, tab_history, tab_recipes = st.tabs(["📝 Daily Log", "📊 Dashboard", "📜 History", "🍳 Recipes"])

# ==========================================
# TAB 1: DAILY LOG
# ==========================================
with tab_log:
    st.header("Log Food")
    
    col_date, col_totals = st.columns([1, 2])
    with col_date:
        selected_date = st.date_input("🗓️ Viewing & Adding to Date:", date.today())
        st.caption(f"**{selected_date.strftime('%A')}**")
        
    # Load today's data early to show totals
    todays_logs = db.get_logs_by_date(selected_date)
    totals = calculate_totals(todays_logs)
    
    with col_totals:
        st.subheader(f"Totals for {selected_date.strftime('%b %d')}")
        mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
        mcol1.metric("Calories", f"{totals['calories']:.0f}")
        mcol2.metric("Protein (g)", f"{totals['protein']:.1f}")
        mcol3.metric("Fat (g)", f"{totals['fat']:.1f}")
        mcol4.metric("Carbs (g)", f"{totals['carbs']:.1f}")
        mcol5.metric("Fiber (g)", f"{totals['fiber']:.1f}")

    st.divider()
    
    # Input Area
    st.subheader("Paste Gemini Output")
    
    # We use a changing key to forcefully clear the text area after a save
    if "paste_key" not in st.session_state:
        st.session_state["paste_key"] = 0
        
    raw_text = st.text_area("Paste table here:", height=150, key=f"paste_area_{st.session_state['paste_key']}",
                            placeholder="""Food Item Calories Protein (g) Fat (g) Carbs (g) Fiber (g)
Fruit & Spinach Smoothie 138 2.2 0.6 34.5 6.4
Greek Yogurt (40g) 38 1.6 3.6 1.5 0.0""")
    
    if st.button("Preview Parsed Data", type="primary"):
        if raw_text:
            parsed_df = parse_gemini_table(raw_text)
            if not parsed_df.empty:
                st.session_state['parsed_df'] = parsed_df
                st.success(f"Parsed {len(parsed_df)} items.")
            else:
                st.error("Could not parse any items. Check the format.")
        else:
            st.warning("Please paste some text first.")
            
    if 'parsed_df' in st.session_state:
        st.info(f"Will save to: **{selected_date.strftime('%A, %Y-%m-%d')}**. Change the date above if you meant a different day.")
        st.dataframe(st.session_state['parsed_df'], use_container_width=True)
        if st.button("💾 Save to Log"):
            db.save_logs(st.session_state['parsed_df'], selected_date)
            del st.session_state['parsed_df']
            
            # Increment key to clear text box
            st.session_state["paste_key"] += 1
            
            st.success("Saved! Refreshing...")
            st.rerun()
            
    st.divider()
    st.subheader(f"Logged Items for {selected_date.strftime('%A, %Y-%m-%d')}")
    if not todays_logs.empty:
        # Create a copy with boolean columns for selection and deletion
        edit_df = todays_logs.copy()
        edit_df.insert(0, "✅ Select", False)
        edit_df.insert(1, "🗑️ Delete", False)
        
        edited_df = st.data_editor(
            edit_df,
            hide_index=True,
            column_config={
                "✅ Select": st.column_config.CheckboxColumn(required=True),
                "🗑️ Delete": st.column_config.CheckboxColumn(required=True),
                "id": None, # Hide ID
                "date": None # Hide date column since it's redundant here
            },
            disabled=["food_name", "calories", "protein", "fat", "carbs", "fiber"],
            use_container_width=True
        )
        
        col_act1, col_act2 = st.columns(2)
        
        # Action: Create Recipe
        selected_items = edited_df[edited_df["✅ Select"] == True]
        with col_act1:
            if not selected_items.empty:
                if st.button("➕ Create Recipe from Selected", type="primary"):
                    st.session_state["recipe_builder_items"] = selected_items.to_dict('records')
                    st.success("Items ready! Go to the 'Recipes' tab to name and save your dish.")
                    
        # Action: Delete
        items_to_delete = edited_df[edited_df["🗑️ Delete"] == True]["id"].tolist()
        with col_act2:
            if items_to_delete:
                if st.button("🗑️ Delete Selected Items"):
                    db.delete_logs(items_to_delete)
                    st.success("Logs deleted! Refreshing...")
                    st.rerun()
    else:
        st.info("No items logged for this date yet.")


# ==========================================
# TAB 2: DASHBOARD
# ==========================================
with tab_dash:
    st.header("Trends")
    
    col_dash1, col_dash2 = st.columns([1, 2])
    with col_dash1:
        view_days = st.radio("Default Zoom Range:", [7, 28], index=0, horizontal=True)
        
    # Load 90 days to allow scrolling inside the zoom window
    recent_logs = db.get_recent_logs(90)
    
    if recent_logs.empty:
        st.info("No data available to display yet.")
    else:
        # Group by date
        daily_summary = recent_logs.groupby('date')[['calories', 'protein', 'fat', 'carbs', 'fiber']].sum().reset_index()
        
        st.subheader("Daily Intake Trends")
        
        # Calculate proportional heights of macros to match total calories
        est_k = daily_summary['protein']*4 + daily_summary['fat']*9 + daily_summary['carbs']*4
        # Avoid division by zero
        est_k = est_k.replace(0, 1)

        p_cal = daily_summary['calories'] * (daily_summary['protein']*4 / est_k)
        f_cal = daily_summary['calories'] * (daily_summary['fat']*9 / est_k)
        c_cal = daily_summary['calories'] * (daily_summary['carbs']*4 / est_k)
        
        # Ensure zero handling
        p_cal = p_cal.fillna(0)
        f_cal = f_cal.fillna(0)
        c_cal = c_cal.fillna(0)
        
        # Create figure with 2 subplots separated by the X axis
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.0,
            row_heights=[0.8, 0.2]
        )

        # 1. Protein (Stacked Area - Gold) #F1A512
        fig.add_trace(
            go.Scatter(x=daily_summary['date'], y=p_cal, 
                       name="Protein", mode='lines', stackgroup='one', line_shape='spline',
                       fillcolor='#F1A512', line=dict(color='#F1A512', width=2),
                       customdata=daily_summary['protein'],
                       hovertemplate='Protein: %{customdata:.1f}g (~%{y:.0f} kcal)<extra></extra>'),
            row=1, col=1
        )
        
        # 2. Carbs (Stacked Area - Red/Orange) #DD4111
        fig.add_trace(
            go.Scatter(x=daily_summary['date'], y=c_cal, 
                       name="Carbs", mode='lines', stackgroup='one', line_shape='spline',
                       fillcolor='#DD4111', line=dict(color='#DD4111', width=2),
                       customdata=daily_summary['carbs'],
                       hovertemplate='Carbs: %{customdata:.1f}g (~%{y:.0f} kcal)<extra></extra>'),
            row=1, col=1
        )
        
        # 3. Fat (Stacked Area - Maroon) #8C0027
        fig.add_trace(
            go.Scatter(x=daily_summary['date'], y=f_cal, 
                       name="Fat", mode='lines', stackgroup='one', line_shape='spline',
                       fillcolor='#8C0027', line=dict(color='#8C0027', width=2),
                       customdata=daily_summary['fat'],
                       hovertemplate='Fat: %{customdata:.1f}g (~%{y:.0f} kcal)<extra></extra>'),
            row=1, col=1
        )

        # 4. Fiber - smoothed filled area chart descending (Teal) #2BAF90
        fig.add_trace(
            go.Scatter(x=daily_summary['date'], y=daily_summary['fiber'], 
                       name="Fiber", mode='lines', fill='tozeroy', line_shape='spline',
                       fillcolor='rgba(43, 175, 144, 0.4)', line=dict(color='#2BAF90', width=2),
                       customdata=daily_summary['fiber'],
                       hovertemplate='Fiber: %{customdata:.1f}g<extra></extra>'),
            row=2, col=1
        )

        # Configure layout (Shrunk height, Legend at bottom)
        fig.update_layout(
            height=400,
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
            margin=dict(t=20, b=50) # Tighter top margin, room for legend at bottom
        )
        
        # Calculate viewport for zoom
        latest_date = pd.to_datetime(daily_summary['date'].max())
        start_date = latest_date - pd.Timedelta(days=view_days - 1)
        
        # Apply zoom to the shared x-axes
        fig.update_xaxes(range=[start_date.strftime('%Y-%m-%d'), latest_date.strftime('%Y-%m-%d')])
        
        # X-axes line styling
        fig.update_xaxes(showline=True, linewidth=1, linecolor='gray', showticklabels=False, row=1, col=1)
        fig.update_xaxes(showline=False, showticklabels=True, row=2, col=1)
        
        # Y-axes setup
        fig.update_yaxes(title_text="KCal", rangemode="tozero", row=1, col=1)
        # Reverse the fiber axis so it hangs down from the shared X line
        fig.update_yaxes(title_text="Fiber (g)", autorange="reversed", row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)
        
        # Data Export
        st.divider()
        st.subheader("Export Everything")
        all_data = db.load_all_logs()
        csv = all_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Complete Log as CSV",
            data=csv,
            file_name='macro_logs.csv',
            mime='text/csv',
        )

# ==========================================
# TAB 3: HISTORY
# ==========================================
with tab_history:
    st.header("📜 Log History")
    
    # Load recent logs
    history_logs = db.get_recent_logs(90) # Load up to 90 days for history

    if history_logs.empty:
        st.info("No history available to display yet.")
    else:
        # Sort history to be most recent first
        history_logs = history_logs.sort_values(by='date', ascending=False)
        
        # Colors for daily backgrounds: #A1D4B1, #F1A512, #DD4111, #8C0027
        # Converted to rgba for Streamlit background styling (transparency 0.2)
        row_colors = [
            'rgba(161, 212, 177, 0.2)',
            'rgba(241, 165, 18, 0.2)',
            'rgba(221, 65, 17, 0.2)',
            'rgba(140, 0, 39, 0.2)'
        ]
        
        # Group by date to keep days together
        grouped = history_logs.groupby('date', sort=False)
        
        # Counter to cycle colors
        color_idx = 0
        
        for log_date, group_df in grouped:
            st.subheader(f"{log_date}")
            
            # Prepare dataframe for display
            display_df = group_df.copy()
            # Move the Select to far right, don't include Delete
            display_df.insert(len(display_df.columns), "✅ Select for Recipe", False)
            
            # Styling function for the backgrounds
            def style_bg(row, c_idx):
                return [f'background-color: {row_colors[c_idx]}'] * len(row)

            # Need to pass color_idx in directly, so we use a lambda or freeze it
            styled_df = display_df.style.apply(style_bg, c_idx=color_idx, axis=1)
            
            # Show editable dataframe so we can catch selections
            edited_history = st.data_editor(
                styled_df,
                hide_index=True,
                column_config={
                    "✅ Select for Recipe": st.column_config.CheckboxColumn(required=True),
                    "id": None, # Hide ID
                    "date": None, # Date is in subheader
                },
                disabled=["food_name", "calories", "protein", "fat", "carbs", "fiber"],
                use_container_width=True,
                key=f"history_table_{log_date}"
            )
            
            # Check for selections to send to recipe builder
            selected_items = edited_history[edited_history["✅ Select for Recipe"] == True]
            if not selected_items.empty:
                if st.button(f"➕ Create Recipe from {log_date} Selections", type="primary", key=f"hist_btn_{log_date}"):
                    current = st.session_state.get("recipe_builder_items", [])
                    st.session_state["recipe_builder_items"] = current + selected_items.drop(columns=["✅ Select for Recipe"]).to_dict('records')
                    st.success("Items ready! Go to the 'Recipes' tab to name and save your dish.")
            
            # Increment color index
            color_idx = (color_idx + 1) % len(row_colors)
            st.write("") # Spacer

# ==========================================
# TAB 4: RECIPES
# ==========================================
with tab_recipes:
    st.header("Batch Cooking & Recipes")
    st.write("Save combinations of ingredients as a single item for easy logging later.")
    
    all_recipes = db.get_all_recipes()
    
    col_add, col_view = st.columns([1, 1])
    
    with col_add:
        st.subheader("Recipe Builder")
        
        # 1. Build from pasted text
        with st.expander("Import from Paste", expanded=False):
            if "recipe_import_key" not in st.session_state:
                st.session_state["recipe_import_key"] = 0
                
            recipe_text = st.text_area("Paste ingredients (Gemini table format):", height=150, key=f"recipe_paste_area_{st.session_state['recipe_import_key']}")
            if st.button("Import Text"):
                if recipe_text:
                    parsed_recipe = parse_gemini_table(recipe_text)
                    if not parsed_recipe.empty:
                        # Append to builder
                        current = st.session_state.get("recipe_builder_items", [])
                        st.session_state["recipe_builder_items"] = current + parsed_recipe.to_dict('records')
                        
                        # Increment key to clear text area
                        st.session_state["recipe_import_key"] += 1
                        st.rerun()

        # 2. Manage current builder items
        st.write("### Current Ingredients")
        builder_items = st.session_state.get("recipe_builder_items", [])
        
        if not builder_items:
            st.info("No ingredients selected. Select items from the Daily Log tab or import from text above.")
        else:
            builder_df = pd.DataFrame(builder_items)
            # Ensure columns exist before displaying
            cols = ['food_name', 'calories', 'protein', 'fat', 'carbs', 'fiber']
            builder_df = builder_df[[c for c in cols if c in builder_df.columns]]
            
            # Let user edit the ingredients (e.g. change proportions/calories manually)
            edited_recipe_df = st.data_editor(builder_df, num_rows="dynamic", use_container_width=True)
            
            # Dynamic totals
            rtotals = calculate_totals(edited_recipe_df)
            st.write(f"**Total:** {rtotals['calories']:.0f} cal | {rtotals['protein']:.1f}g P | {rtotals['fat']:.1f}g F | {rtotals['carbs']:.1f}g C | {rtotals['fiber']:.1f}g Fiber")
            
            if "recipe_name_key" not in st.session_state:
                st.session_state["recipe_name_key"] = 0
            
            recipe_name = st.text_input("Name your dish:", key=f"recipe_name_{st.session_state['recipe_name_key']}")
            
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                if st.button("💾 Save Dish", type="primary"):
                    if recipe_name and not edited_recipe_df.empty:
                        db.save_recipe(recipe_name, edited_recipe_df)
                        st.session_state["recipe_builder_items"] = [] # Clear builder
                        st.session_state["recipe_name_key"] += 1 # Clear name input
                        st.success(f"Saved dish '{recipe_name}'!")
                        st.rerun()
                    else:
                        st.warning("Please provide a name and ensure there are ingredients.")
            with col_s2:
                if st.button("Clear Ingredients"):
                    st.session_state["recipe_builder_items"] = []
                    st.rerun()

    with col_view:
        st.subheader("Saved Recipes")
        if all_recipes.empty:
            st.info("No recipes saved yet.")
        else:
            for _, row in all_recipes.iterrows():
                with st.expander(f"📦 {row['name']} ({row['calories']:.0f} cal)"):
                    st.write(f"**Base Macros:** {row['protein']:.1f}g P | {row['fat']:.1f}g F | {row['carbs']:.1f}g C")
                    
                    # Convert the JSON string back to DataFrame for display
                    if 'ingredients_json' in row:
                        ing_df = pd.read_json(row['ingredients_json'], orient='records')
                        
                        # Make the dataframe editable so users can tweak individual amounts
                        st.write("Tune ingredients for this specific meal:")
                        edited_ing_df = st.data_editor(ing_df, key=f"editor_{row['name']}", use_container_width=True)
                        
                        # Calculate the new base totals from the edited dataframe
                        new_base_totals = calculate_totals(edited_ing_df)
                        
                        # Add a global portion multiplier
                        portion = st.number_input(
                            f"Portion Multiplier for '{row['name']}'", 
                            min_value=0.1, 
                            value=1.0, 
                            step=0.1, 
                            key=f"portion_{row['name']}"
                        )
                        
                        # Display what the final logged amounts will be
                        final_cal = new_base_totals['calories'] * portion
                        st.caption(f"**Logging:** {final_cal:.0f} cal | " 
                                   f"{new_base_totals['protein'] * portion:.1f}g P | "
                                   f"{new_base_totals['fat'] * portion:.1f}g F | "
                                   f"{new_base_totals['carbs'] * portion:.1f}g C")
                        
                        # Button to log this recipe TODAY
                        if st.button(f"Log '{row['name']}' Today", key=f"log_{row['name']}"):
                            # Construct a single row df for the recipe, applying the multiplier
                            recipe_name = f"Recipe: {row['name']}"
                            if portion != 1.0:
                                recipe_name += f" ({portion}x portion)"
                                
                            recipe_log = pd.DataFrame([{
                                'food_name': recipe_name,
                                'calories': final_cal,
                                'protein': new_base_totals['protein'] * portion,
                                'fat': new_base_totals['fat'] * portion,
                                'carbs': new_base_totals['carbs'] * portion,
                                'fiber': new_base_totals['fiber'] * portion
                            }])
                            db.save_logs(recipe_log, date.today())
                            st.success(f"Logged '{recipe_name}' to today's log!")

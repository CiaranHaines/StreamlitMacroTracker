import pandas as pd
from datetime import date
import streamlit as st
from sqlalchemy import create_engine, text

@st.cache_resource
def get_engine():
    db_url = st.secrets["connections"]["supabase"]["url"]
    return create_engine(db_url)

def init_db():
    # Tables are manually created in Supabase. The app user does not have CREATE permissions.
    pass

def save_logs(df: pd.DataFrame, log_date: date):
    if df.empty:
        return
        
    df = df.copy()
    df['date'] = log_date
    
    engine = get_engine()
    df.to_sql('logs', engine, if_exists='append', index=False)

def get_logs_by_date(log_date: date) -> pd.DataFrame:
    engine = get_engine()
    query = text("SELECT * FROM logs WHERE date = :date")
    return pd.read_sql_query(query, engine, params={'date': log_date})

def get_recent_logs(days: int = 30) -> pd.DataFrame:
    engine = get_engine()
    query = text("SELECT * FROM logs WHERE date >= CURRENT_DATE - (:days * INTERVAL '1 day')")
    return pd.read_sql_query(query, engine, params={'days': days})

def load_all_logs() -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql_query(text("SELECT * FROM logs"), engine)

def delete_logs(log_ids: list):
    if not log_ids:
        return
    engine = get_engine()
    with engine.begin() as conn:
        placeholders = ', '.join([f':id{i}' for i in range(len(log_ids))])
        params = {f'id{i}': log_id for i, log_id in enumerate(log_ids)}
        conn.execute(text(f"DELETE FROM logs WHERE id IN ({placeholders})"), params)

def save_recipe(name: str, df: pd.DataFrame):
    if df.empty:
        return
        
    totals = df[['calories', 'protein', 'fat', 'carbs', 'fiber']].sum()
    ingredients_json = df.to_json(orient='records')
    
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(
            '''INSERT INTO recipes 
               (name, ingredients_json, calories, protein, fat, carbs, fiber) 
               VALUES (:name, :ingredients_json, :calories, :protein, :fat, :carbs, :fiber)
               ON CONFLICT (name) DO UPDATE SET
               ingredients_json = EXCLUDED.ingredients_json,
               calories = EXCLUDED.calories,
               protein = EXCLUDED.protein,
               fat = EXCLUDED.fat,
               carbs = EXCLUDED.carbs,
               fiber = EXCLUDED.fiber
            '''
        ), {
            'name': name,
            'ingredients_json': ingredients_json,
            'calories': totals['calories'],
            'protein': totals['protein'],
            'fat': totals['fat'],
            'carbs': totals['carbs'],
            'fiber': totals['fiber']
        })

def get_all_recipes() -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql_query(text("SELECT * FROM recipes"), engine)

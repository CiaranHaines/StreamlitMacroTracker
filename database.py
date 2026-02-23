import pandas as pd
from datetime import date, timedelta
import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)

def init_db():
    # Tables are manually created in Supabase. The app user does not have CREATE permissions.
    pass

def save_logs(df: pd.DataFrame, log_date: date):
    if df.empty:
        return
        
    df = df.copy()
    df['date'] = log_date.strftime('%Y-%m-%d')
    records = df.to_dict(orient='records')
    
    supabase = get_supabase()
    supabase.table('logs').insert(records).execute()

def get_logs_by_date(log_date: date) -> pd.DataFrame:
    supabase = get_supabase()
    date_str = log_date.strftime('%Y-%m-%d')
    response = supabase.table('logs').select("*").eq("date", date_str).execute()
    return pd.DataFrame(response.data)

def get_recent_logs(days: int = 30) -> pd.DataFrame:
    supabase = get_supabase()
    cutoff_date = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
    response = supabase.table('logs').select("*").gte("date", cutoff_date).execute()
    return pd.DataFrame(response.data)

def load_all_logs() -> pd.DataFrame:
    supabase = get_supabase()
    # Note: Supabase REST limits to 1000 rows by default. For a massive scale app, 
    # pagination would be needed, but this is fine for personal use.
    response = supabase.table('logs').select("*").limit(10000).execute()
    return pd.DataFrame(response.data)

def delete_logs(log_ids: list):
    if not log_ids:
        return
    supabase = get_supabase()
    # Supabase REST 'in_' filter takes a list
    supabase.table('logs').delete().in_("id", log_ids).execute()

def save_recipe(name: str, df: pd.DataFrame):
    if df.empty:
        return
        
    totals = df[['calories', 'protein', 'fat', 'carbs', 'fiber']].sum()
    ingredients_json = df.to_json(orient='records')
    
    supabase = get_supabase()
    record = {
        'name': name,
        'ingredients_json': ingredients_json,
        'calories': totals['calories'],
        'protein': totals['protein'],
        'fat': totals['fat'],
        'carbs': totals['carbs'],
        'fiber': totals['fiber']
    }
    
    # Supabase 'upsert' works on unique constraints (name is UNIQUE)
    supabase.table('recipes').upsert(record).execute()

def get_all_recipes() -> pd.DataFrame:
    supabase = get_supabase()
    response = supabase.table('recipes').select("*").execute()
    return pd.DataFrame(response.data)

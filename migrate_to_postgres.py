import sqlite3
import pandas as pd
from sqlalchemy import create_engine
import os

# Read url directly
secrets_path = os.path.join(".streamlit", "secrets.toml")
if not os.path.exists(secrets_path):
    print(f"Cannot find secrets file at {secrets_path}")
    exit(1)

pg_url = ""
with open(secrets_path, "r") as f:
    for line in f:
        if line.strip().startswith('url'):
            # Basic parsing for url = "..."
            pg_url = line.split('=')[1].strip().strip('"').strip("'")
            break

if not pg_url:
    print("Could not find the 'url' property in the secrets file!")
    exit(1)

print(f"Connecting to Postgres using URL found in secrets...")
pg_engine = create_engine(pg_url)

# SQLite
sqlite_path = "macros.db"
if not os.path.exists(sqlite_path):
    print("No local SQLite database found to migrate.")
    exit(0)

sqlite_conn = sqlite3.connect(sqlite_path)

print("Migrating logs...")
try:
    logs_df = pd.read_sql_query("SELECT * FROM logs", sqlite_conn)
    if not logs_df.empty:
        # We drop the ID so that Postgres can assign its own auto-incrementing primary key
        # since postgres sequences could get out of sync otherwise.
        if 'id' in logs_df.columns:
            logs_df = logs_df.drop(columns=['id'])
        logs_df['date'] = pd.to_datetime(logs_df['date']).dt.date
        logs_df.to_sql('logs', pg_engine, if_exists='append', index=False)
        print(f"Successfully migrated {len(logs_df)} logs.")
    else:
        print("No logs found to migrate.")
except Exception as e:
    print(f"Error migrating logs: {e}")

print("Migrating recipes...")
try:
    recipes_df = pd.read_sql_query("SELECT * FROM recipes", sqlite_conn)
    if not recipes_df.empty:
        if 'id' in recipes_df.columns:
            recipes_df = recipes_df.drop(columns=['id'])
        recipes_df.to_sql('recipes', pg_engine, if_exists='append', index=False)
        print(f"Successfully migrated {len(recipes_df)} recipes.")
    else:
        print("No recipes found to migrate.")
except Exception as e:
    print(f"Error migrating recipes: {e}")

print("Migration complete!")

import psycopg2
from psycopg2 import sql
from IPython.display import display, HTML, Markdown
import pandas as pd
import csv
import os
import json

db_name = "wellness_tracker"
CREATE_TABLES_FILE = r"C:\Users\Rebecca\OneDrive\Documents\Python AI\Wellness Tracker\sql\Create_tables.sql"
POPULATE_DIM_TABLES_FILE = r"C:\Users\Rebecca\OneDrive\Documents\Python AI\Wellness Tracker\sql\Populate_dim_tables.sql"
# currently not using this approach, (using a dropdown in the GUI instead), but keeping it here for now in case I want to use it later.
VIEWS_FILE = r"C:\Users\Rebecca\OneDrive\Documents\Python AI\Wellness Tracker\sql\Combo_Views.sql"

# Load config
def load_config():
    with open("config.json") as f:
        return json.load(f)



# Create a database connection
def get_connection():
    
    CONFIG = load_config()  
    return psycopg2.connect(
        dbname=db_name,
        user=CONFIG["db_user"],
        password=CONFIG["db_password"],
        host=CONFIG["db_host"],
        port=CONFIG["db_port"],
    )


# Run a SQL file
def run_sql_file(file_path):
    """Execute a SQL file against the target database."""

    sql_path = os.path.abspath(file_path)

    with open(sql_path, "r", encoding="utf-8") as f:
        sql_text = f.read()

    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Split statements to avoid multi-statement issues
        commands = sql_text.split(";")
        # Remove last statement as it is likely empty due to the trailing
        commands = commands[:-1]

        for command in commands:
            # Only run this if the command is NOT empty after removing whitespace
            if command.strip():
                cur.execute(command)
                print(f"✅ Statement executed: {command.strip()[:50]}...")

        conn.commit()
        cur.close()

        print(f"✅ SQL applied: {sql_path}")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ SQL file error: {e}")
        raise

    finally:
        if conn:
            conn.close()


def run_select(query, return_df=True, to_csv_path=None):
    """
    Run SELECT query.
    - return_df=True  -> returns pandas DataFrame
    - return_df=False -> returns (rows, columns)
    """
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        
        # cursor.fetchall() returns a list of tuples, where each tuple represents a row. 
        # cursor.description provides metadata about the columns, where desc[0] is the column name.
        rows = cursor.fetchall()
        columns = [x[0] for x in cursor.description]
        
        if to_csv_path:
            # the current code is only good for rewriteing, not appending. 
            # If you want to support appending, you can check if the file exists and write header only if it doesn't.
            with open(to_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(rows)
            print(f"✅ CSV written: {to_csv_path}")

        cursor.close()

        if return_df:
            return pd.DataFrame(rows, columns=columns)
        return rows, columns

    except Exception as e:
        print(f"❌ SELECT error: {e}")
        return pd.DataFrame() if return_df else ([])
    finally:
        if conn:
            conn.close()



def run_ddl_dml(query, params=None):
    """
    Run INSERT/UPDATE/DELETE/CREATE/DROP/ALTER query (parameterized).
    Returns affected row count (if available).
    If raise_on_error=True, re-raises the exception so you see the full traceback.
    """
    conn = None
    try:
        conn = get_connection()
        with conn:  # auto-commit on success, auto-rollback on error
            with conn.cursor() as cursor:
                # pyscopg2 will handle the parameter substitution safely, preventing SQL injection.
                # The caller function (e.g., insert_food_log) will pass the params when calling this function.
                cursor.execute(query, params)
                return cursor.rowcount

    except Exception as e:
         # Print a Postgres-provided message if available, then re-raise
        pg_msg = getattr(e, "pgerror", None) or str(e)
        print(f"DDL/DML error: {pg_msg}")
        raise
       

        
    finally:
        if conn:
            conn.close()


def initiate_database():
    """
    Create the database name
    Connects to the existing 'postgres' database to do the creation.
    """
    CONFIG = load_config()

    conn = None
    try:
        # connect to an existing DB first
        conn = psycopg2.connect(
            dbname="postgres",
            user=CONFIG["db_user"],
            password=CONFIG["db_password"],
            host=CONFIG["db_host"],
            port=CONFIG["db_port"],
        )
        conn.autocommit = True

        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", ("wellness_tracker",))
        exists = cur.fetchone() is not None

        if not exists:
            cur.execute(sql.SQL("CREATE DATABASE wellness_tracker;"))
            run_sql_file(CREATE_TABLES_FILE)
            print("✅ Database created: wellness_tracker")
        else:
            print("ℹ️ Database already exists: wellness_tracker")

        cur.close()
    finally:
        if conn:
            conn.close()

    
    run_sql_file(POPULATE_DIM_TABLES_FILE)

    # Optional: if you've generated aliases, load them too.
    # currently not using this approach, (using a dropdown in the GUI instead), but keeping it here for now in case I want to use it later.
    # if os.path.exists(POPULATE_FOOD_ALIASES_FILE):
    #  run_sql_file(POPULATE_FOOD_ALIASES_FILE)

if __name__ == "__main__":
    initiate_database()
    print('✅ Database initialization complete.')
    run_sql_file(VIEWS_FILE )
    

    


  

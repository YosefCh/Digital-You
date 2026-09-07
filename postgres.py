import psycopg2
from psycopg2 import sql
from IPython.display import display, HTML, Markdown
import pandas as pd
import csv
import os
import json

ADMIN_DB_NAME = "postgres"
DB_NAME = "DEV_wellness_tracker"
CREATE_TABLES_FILE = r"C:\Users\Rebecca\OneDrive\Documents\Python AI\Wellness Tracker\sql\Create_tables.sql"
POPULATE_DIM_TABLES_FILE = r"C:\Users\Rebecca\OneDrive\Documents\Python AI\Wellness Tracker\sql\Populate_dim_tables.sql"
# currently not using this approach, (using a dropdown in the GUI instead), but keeping it here for now in case I want to use it later.


# Load config
def load_config():
    with open("config.json") as f:
        return json.load(f)



# Create a database connection
def get_connection(database_name=DB_NAME):
    
    CONFIG = load_config()  
    return psycopg2.connect(
        dbname=database_name,
        user=CONFIG["db_user"],
        password=CONFIG["db_password"],
        host=CONFIG["db_host"],
        port=CONFIG["db_port"],
    )


# Run a SQL file
def run_sql_file(file_path, database_name=DB_NAME):
    """Execute a SQL file against the target database."""

    sql_path = os.path.abspath(file_path)

    with open(sql_path, "r", encoding="utf-8") as f:
        sql_text = f.read()

    conn = None
    try:
        conn = get_connection(database_name)
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


def run_select(query, return_df=True, to_csv_path=None, show_errors=True):
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
      if show_errors:
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


def initiate_database(database_name=DB_NAME):
    """
    Create the database name
    Connects to the existing 'postgres' database to do the creation.
    """
    CONFIG = load_config()

    conn = None
    try:
        # connect to an existing DB first
        conn = psycopg2.connect(
            dbname=ADMIN_DB_NAME,
            user=CONFIG["db_user"],
            password=CONFIG["db_password"],
            host=CONFIG["db_host"],
            port=CONFIG["db_port"],
        )
        conn.autocommit = True

        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (database_name,))
        exists = cur.fetchone() is not None

        if not exists:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
            run_sql_file(CREATE_TABLES_FILE, database_name=database_name)
            print(F"✅ Database created: {database_name}")
        else:
            print(f"ℹ️ Database already exists: {database_name}")
        cur.close()
    finally:
        if conn:
            conn.close()

    
    run_sql_file(POPULATE_DIM_TABLES_FILE, database_name=database_name)


def reset_database(database_name, action):
    """
    Drops or truncates the database and recreates it.
    """
    CONFIG = load_config()
    
    if database_name == ADMIN_DB_NAME:
                raise ValueError(f"Cannot drop the admin database: {ADMIN_DB_NAME}")
            
    if action not in ("reset", "truncate"):
        action = input("Enter action ('reset' or 'truncate'): ").strip().lower()
    if action not in ("reset", "truncate"):
        print("Aborted: invalid action.")
        return
    
    conn = None
    try:
        # connect to an existing DB first
        conn = psycopg2.connect(
            dbname=ADMIN_DB_NAME,
            user=CONFIG["db_user"],
            password=CONFIG["db_password"],
            host=CONFIG["db_host"],
            port=CONFIG["db_port"],
        )
        conn.autocommit = True

        cur = conn.cursor() 
        
        if (database_name.upper().count('LIVE') == 1 
           or database_name.upper().count('LIV') == 1
           or database_name.upper().count('DIGITAL') == 1
           or database_name.upper().count('YOU') == 1
           or (database_name.upper().count('DEV') == 0 and database_name.upper().count('TEST') == 0)):
            c1 = input(f"WARNING: '{database_name}' looks production-like. Type 'YES' to continue: ").strip()
            if c1 != 'YES':
                print("Aborted: user chose not to continue.")
                return
        else:
            if action == "reset":
                cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name)))
                print(f"✅ Database dropped: {database_name}")
                
                # now reset the database by calling the initiate_database function
                initiate_database(database_name=database_name)
                
            # action is trunate
            else:
                cur.close()
                conn.close()
                
                # Connect directly to the database we want to truncate
                conn = get_connection(database_name)
                
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT table_schema, table_name
                        FROM information_schema.tables
                        WHERE table_type = 'BASE TABLE'
                        AND table_schema NOT IN ('pg_catalog', 'information_schema');
                        """
                    )
                
                    tables = cur.fetchall()

                    cur.execute(
                        """
                        SELECT table_schema, table_name
                        FROM information_schema.views
                        WHERE table_schema NOT IN ('pg_catalog', 'information_schema');
                        """
                    )
                    views = cur.fetchall()    
                    
                    if not tables and not views:
                        print(f"No user tables/views found in {database_name}. Nothing to do.")
                        return
                    
                    idents = [sql.Identifier(s, n) for s, n in tables]
                    cur.execute(sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE;").format(sql.SQL(", ").join(idents)))
                    print(f"Truncated {len(tables)} tables (identities restarted).")

                    idents = [sql.Identifier(s, n) for s, n in views]
                    cur.execute(sql.SQL("DROP VIEW IF EXISTS {} CASCADE;").format(sql.SQL(", ").join(idents)))
                    print(f"Dropped {len(views)} views.")
                
                conn.commit()
                    
                run_sql_file(POPULATE_DIM_TABLES_FILE, database_name=database_name)
                print(f"✅ Database truncated and dimension tables re-populated: {database_name}")
                    


        cur.close()
    finally:
        if conn:
            conn.close()

    print(f"✅ Database reset complete: {database_name}")




if __name__ == "__main__":
    initiate_database()
    print('✅ Database initialization complete.')

    

    


  

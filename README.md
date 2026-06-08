# Data

Put your CSV catalogs here (foods, exercises, etc.).

Suggested patterns:

- `foods.csv`: your personal food catalog (macros)
- `exercises.csv`: your exercise catalog

You can ingest them into DuckDB using `wellness_tracker.ingest`.

## Food aliases (user input matching)

The database supports a `food_alias` table that maps user-friendly / misspelled inputs back to a canonical `food(food_id)`.

1) Create tables (includes `food_alias`):

- Run `postgres.py` (or execute `sql/Create_tables.sql` against your DB).

1) Generate alias inserts from a CSV:

- Prepare a foods CSV with at least:

  - `food_id` (or `id`)
  - `name` (or `food_name` or `food`)

- Optional alias columns (if you already have them):

  - `alias`, `alias1`, `alias2`, ... (or `alias_1`, `alias_2`, ...)
  - or a single `aliases` column with `;`-separated values

Generate the SQL file:

- `python generate_food_alias_inserts.py --input foods.csv --output-sql sql/Populate_food_aliases.sql`

AI-powered aliases (synonyms + plausible misspellings):

- `python generate_food_alias_inserts.py --input foods.csv --output-sql sql/Populate_food_aliases.sql --ai --ai-model gpt-4o-mini`

Then apply it:

- Add a call to `run_sql_file("sql/Populate_food_aliases.sql")` in `postgres.py`, or run that SQL file manually.

## Weather (Open-Meteo)

The notebook includes an example `fetch_today_weather(...)` helper that pulls daily temperature (min/max in Fahrenheit), a simplified conditions label (Clear/Rain/Snow/etc), and a Low/Moderate/High humidity bucket from Open-Meteo.

If the request fails in Python with `CERTIFICATE_VERIFY_FAILED` but works in PowerShell, your network is likely doing HTTPS inspection. Generate a CA bundle from the Windows trusted root store:

- Run `certs/export_windows_root_certs.ps1`

This produces `certs/windows-root-ca.pem`, which the notebook uses for `requests` SSL verification.

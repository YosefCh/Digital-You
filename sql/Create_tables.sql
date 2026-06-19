

-- Dimension tables
-- Food dimension table.
 
CREATE TABLE IF NOT EXISTS food (
  food_id           BIGSERIAL PRIMARY KEY,
  name              TEXT NOT NULL,
  calories          NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (calories >= 0),
  carbohydrates     NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (carbohydrates >= 0),
  proteins       NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (proteins >= 0),
  fats           NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (fats >= 0),
  fiber           NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (fiber >= 0),
  serving_size      NUMERIC(10, 2),
  measurement_unit  TEXT,
  -- `created_at` records when the food item was added
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- `UNIQUE(name)` prevents duplicate food names.
  CONSTRAINT food_name_unique UNIQUE (name)
);


CREATE TABLE IF NOT EXISTS exercise (
  exercise_id    BIGSERIAL PRIMARY KEY,
  exercise_type  TEXT NOT NULL,
  name           TEXT NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT exercise_type_name_unique UNIQUE (exercise_type, name)
);

CREATE TABLE IF NOT EXISTS activity (
  activity_id  BIGSERIAL PRIMARY KEY,
  name         TEXT NOT NULL UNIQUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fact tables
CREATE TABLE IF NOT EXISTS food_log (
  food_log_id  BIGSERIAL PRIMARY KEY,
  log_date     DATE NOT NULL DEFAULT CURRENT_DATE,
  food_id      BIGINT NOT NULL REFERENCES food(food_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  meal_type    TEXT NOT NULL,
  quantity     NUMERIC(10, 1) NOT NULL DEFAULT 1 CHECK (quantity > 0),
  combo_name   TEXT,
  notes        TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT food_log_meal_type_check CHECK (meal_type IN ('Breakfast', 'Lunch', 'Dinner', 'Snack'))
);

CREATE INDEX IF NOT EXISTS food_log_log_date_idx ON food_log (log_date);
CREATE INDEX IF NOT EXISTS food_log_food_id_idx ON food_log (food_id);

-- Prevent duplicate entries of the same food for the same day + meal.
-- (Allows the same food in different combos by including combo_name when present.)
CREATE UNIQUE INDEX IF NOT EXISTS food_log_unique_entry_idx
  ON food_log (log_date, meal_type, food_id, (COALESCE(combo_name, '')));

-- Required for EXCLUDE constraints that use "=" on scalar types (like BIGINT) with GiST
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- ...existing code...

CREATE TABLE IF NOT EXISTS exercise_log (
  exercise_log_id   BIGSERIAL PRIMARY KEY,
  log_date          DATE NOT NULL DEFAULT CURRENT_DATE,
  exercise_id       BIGINT NOT NULL REFERENCES exercise(exercise_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  duration_minutes  INTEGER CHECK (duration_minutes IS NULL OR duration_minutes >= 0),
  notes             TEXT,
  -- Store a UTC timestamp (automatic) so the range expression is immutable-friendly
  created_at_utc    TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),

  -- Block same exercise_id within 30 minutes (based on created_at_utc)
  CONSTRAINT exercise_log_no_dupe_30min
    EXCLUDE USING gist
    (
      exercise_id WITH =,
      tsrange(created_at_utc, created_at_utc + interval '30 minutes', '[)') WITH &&
    )
);

CREATE INDEX IF NOT EXISTS exercise_log_log_date_idx ON exercise_log (log_date);
CREATE INDEX IF NOT EXISTS exercise_log_exercise_id_idx ON exercise_log (exercise_id);

-- ...existing code...
CREATE TABLE IF NOT EXISTS activity_log (
  activity_log_id   BIGSERIAL PRIMARY KEY,
  log_date          DATE NOT NULL DEFAULT CURRENT_DATE,
  activity_id       BIGINT NOT NULL REFERENCES activity(activity_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  duration_minutes  INTEGER CHECK (duration_minutes IS NULL OR duration_minutes >= 0),
  notes             TEXT,
  -- Store a UTC timestamp (automatic) so the range expression is immutable-friendly
  created_at_utc    TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),

  -- Block same activity_id within 30 minutes (based on created_at_utc)
  CONSTRAINT activity_log_no_dupe_30min
    EXCLUDE USING gist
    (
      activity_id WITH =,
      tsrange(created_at_utc, created_at_utc + interval '30 minutes', '[)') WITH &&
    )
);


CREATE INDEX IF NOT EXISTS activity_log_log_date_idx ON activity_log (log_date);
CREATE INDEX IF NOT EXISTS activity_log_activity_id_idx ON activity_log (activity_id);

CREATE TABLE IF NOT EXISTS stress_log (
  stress_log_id        BIGSERIAL PRIMARY KEY,
  log_date             DATE NOT NULL DEFAULT CURRENT_DATE,
  work_stress_level    TEXT,
  work_productivity_level TEXT,
  family_stress_level  TEXT,
  health_stress_level  TEXT,
  other_stress_level   TEXT,
  notes                TEXT,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT stress_log_one_per_day UNIQUE (log_date)
);

CREATE INDEX IF NOT EXISTS stress_log_log_date_idx ON stress_log (log_date);

CREATE TABLE IF NOT EXISTS sleep_log (
  sleep_log_id              BIGSERIAL PRIMARY KEY,
  log_date                  DATE NOT NULL DEFAULT CURRENT_DATE,
  bedtime                   TIMESTAMPTZ,
  wake_time                 TIMESTAMPTZ,
  interruptions             SMALLINT CHECK (interruptions IS NULL OR (interruptions BETWEEN 0 AND 20)),
  total_interruption_minutes INTEGER CHECK (total_interruption_minutes IS NULL OR total_interruption_minutes >= 0),
  notes                     TEXT,
  created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT sleep_log_time_order CHECK (
    bedtime IS NULL OR wake_time IS NULL OR wake_time >= bedtime
  ),
  CONSTRAINT sleep_log_interruptions_minutes_check CHECK (
    (
      (interruptions IS NULL OR interruptions = 0)
      AND (total_interruption_minutes IS NULL OR total_interruption_minutes = 0)
    )
    OR
    (
      interruptions > 0
      AND total_interruption_minutes IS NOT NULL
      AND total_interruption_minutes >= interruptions * 1 -- Assuming at least 1 minute per interruption
    )
  )
);

CREATE INDEX IF NOT EXISTS sleep_log_log_date_idx ON sleep_log (log_date);

-- Prevent duplicate sleep_log rows (treat NULLs consistently via COALESCE)
CREATE UNIQUE INDEX IF NOT EXISTS sleep_log_exact_duplicate_idx
  ON sleep_log (
    log_date,
    COALESCE(bedtime, 'epoch'::timestamptz),
    COALESCE(wake_time, 'epoch'::timestamptz)
  );


CREATE TABLE IF NOT EXISTS weather_log (
  weather_log_id     BIGSERIAL PRIMARY KEY,
  log_date           DATE NOT NULL DEFAULT CURRENT_DATE,
  temp_min_f         NUMERIC(5, 1),
  temp_max_f         NUMERIC(5, 1),
  humidity_level     TEXT,        -- 'Low' | 'Moderate' | 'High'
  conditions         TEXT,        -- 'Clear' | 'Overcast' | 'Rain' | 'Snow' | etc.
  notes              TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT weather_log_one_per_day UNIQUE (log_date),
  CONSTRAINT weather_log_humidity_level_check CHECK (
    humidity_level IS NULL OR humidity_level IN ('Low', 'Moderate', 'High')
  )
);

CREATE INDEX IF NOT EXISTS weather_log_log_date_idx ON weather_log (log_date);

-- Daily water consumption (one row per day). Use total_oz as a running daily total.
CREATE TABLE IF NOT EXISTS water_log (
  water_log_id  BIGSERIAL PRIMARY KEY,
  log_date      DATE NOT NULL DEFAULT CURRENT_DATE,
  total_oz      NUMERIC(6, 1) NOT NULL DEFAULT 0 CHECK (total_oz >= 0),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT water_log_one_per_day UNIQUE (log_date)
);

CREATE INDEX IF NOT EXISTS water_log_log_date_idx ON water_log (log_date);


CREATE TABLE IF NOT EXISTS hygiene_log (
  hygiene_log_id   BIGSERIAL PRIMARY KEY,
  log_date         DATE NOT NULL DEFAULT CURRENT_DATE,
  brushed          BOOLEAN NOT NULL DEFAULT FALSE,
  flossed          BOOLEAN NOT NULL DEFAULT FALSE,
  showered         BOOLEAN NOT NULL DEFAULT FALSE,
  brushed_time     TEXT,   -- nullable, frontend will supply dropdown values
  flossed_time     TEXT,   -- nullable
  shower_time      TEXT,   -- nullable
  notes            TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT hygiene_log_one_per_day UNIQUE (log_date)
);

CREATE INDEX IF NOT EXISTS hygiene_log_log_date_idx ON hygiene_log (log_date);





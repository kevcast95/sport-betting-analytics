PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS daily_runs (
  daily_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_date TEXT NOT NULL, -- YYYY-MM-DD
  sport TEXT NOT NULL,
  created_at_utc TEXT NOT NULL, -- ISO
  status TEXT NOT NULL CHECK (status IN ('running','complete','failed')),
  UNIQUE(run_date, sport)
);

CREATE TABLE IF NOT EXISTS event_snapshots (
  snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
  sport TEXT NOT NULL DEFAULT 'football', -- mismo slug que daily_runs.sport (football|tennis|…)
  event_id INTEGER NOT NULL,
  dataset TEXT NOT NULL, -- event|lineups|statistics|h2h|team_streaks|team_season_stats|odds_all|odds_featured
  captured_at_utc TEXT NOT NULL, -- ISO
  payload_raw TEXT NOT NULL, -- JSON
  source TEXT,
  UNIQUE(sport, event_id, dataset, captured_at_utc)
);

CREATE TABLE IF NOT EXISTS event_features (
  feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
  sport TEXT NOT NULL DEFAULT 'football',
  event_id INTEGER NOT NULL,
  captured_at_utc TEXT NOT NULL, -- ISO
  features_json TEXT NOT NULL, -- JSON
  processor_versions_json TEXT NOT NULL, -- JSON
  UNIQUE(sport, event_id, captured_at_utc)
);

CREATE TABLE IF NOT EXISTS picks (
  pick_id INTEGER PRIMARY KEY AUTOINCREMENT,
  daily_run_id INTEGER NOT NULL,
  event_id INTEGER NOT NULL,
  market TEXT NOT NULL, -- e.g. 1X2
  selection TEXT NOT NULL, -- 1/X/2 u otras (Over 2.5, 1X, etc.)
  picked_value REAL, -- decimal odds or similar
  odds_reference TEXT, -- JSON
  status TEXT NOT NULL CHECK (status IN ('pending','validated','void')),
  created_at_utc TEXT NOT NULL, -- ISO
  idempotency_key TEXT NOT NULL UNIQUE,
  FOREIGN KEY (daily_run_id) REFERENCES daily_runs(daily_run_id)
);

CREATE TABLE IF NOT EXISTS daily_run_event_model_feedback (
  daily_run_id INTEGER NOT NULL,
  event_id INTEGER NOT NULL,
  model_skip_reason TEXT,
  pipeline_skip_summary TEXT,
  updated_at_utc TEXT NOT NULL,
  PRIMARY KEY (daily_run_id, event_id),
  FOREIGN KEY (daily_run_id) REFERENCES daily_runs(daily_run_id)
);

CREATE TABLE IF NOT EXISTS pick_results (
  pick_id INTEGER PRIMARY KEY,
  validated_at_utc TEXT NOT NULL, -- ISO
  home_score INTEGER,
  away_score INTEGER,
  result_1x2 TEXT CHECK (result_1x2 IN ('1','X','2') OR result_1x2 IS NULL),
  outcome TEXT NOT NULL CHECK (outcome IN ('win','loss','pending')),
  evidence_json TEXT, -- JSON
  FOREIGN KEY (pick_id) REFERENCES picks(pick_id)
);

-- Opcional / básico para backtesting
CREATE TABLE IF NOT EXISTS backtest_runs (
  backtest_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  range_start TEXT NOT NULL, -- YYYY-MM-DD
  range_end TEXT NOT NULL, -- YYYY-MM-DD
  strategy_version TEXT NOT NULL,
  created_at_utc TEXT NOT NULL -- ISO
);

CREATE TABLE IF NOT EXISTS backtest_metrics (
  backtest_run_id INTEGER NOT NULL UNIQUE,
  metrics_json TEXT NOT NULL,
  created_at_utc TEXT NOT NULL,
  FOREIGN KEY (backtest_run_id) REFERENCES backtest_runs(backtest_run_id)
);

-- --- Tracking usuarios / toma de picks / combinaciones sugeridas ---

CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  created_at_utc TEXT NOT NULL,
  bankroll_cop REAL
);

CREATE TABLE IF NOT EXISTS user_pick_decisions (
  user_id INTEGER NOT NULL,
  pick_id INTEGER NOT NULL,
  taken INTEGER NOT NULL CHECK (taken IN (0, 1)),
  updated_at_utc TEXT NOT NULL,
  notes TEXT,
  risk_category TEXT,
  decision_origin TEXT,
  stake_amount REAL,
  user_outcome TEXT CHECK (user_outcome IN ('win','loss','pending') OR user_outcome IS NULL),
  user_outcome_updated_at_utc TEXT,
  realized_return_cop REAL,
  bankroll_delta_applied_cop REAL,
  PRIMARY KEY (user_id, pick_id),
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  FOREIGN KEY (pick_id) REFERENCES picks(pick_id)
);

CREATE TABLE IF NOT EXISTS suggested_combos (
  suggested_combo_id INTEGER PRIMARY KEY AUTOINCREMENT,
  daily_run_id INTEGER NOT NULL,
  rank_order INTEGER NOT NULL CHECK (rank_order IN (1, 2)),
  created_at_utc TEXT NOT NULL,
  strategy_note TEXT,
  UNIQUE (daily_run_id, rank_order),
  FOREIGN KEY (daily_run_id) REFERENCES daily_runs(daily_run_id)
);

CREATE TABLE IF NOT EXISTS suggested_combo_legs (
  suggested_combo_id INTEGER NOT NULL,
  pick_id INTEGER NOT NULL,
  leg_order INTEGER NOT NULL,
  PRIMARY KEY (suggested_combo_id, pick_id),
  FOREIGN KEY (suggested_combo_id) REFERENCES suggested_combos(suggested_combo_id) ON DELETE CASCADE,
  FOREIGN KEY (pick_id) REFERENCES picks(pick_id)
);

CREATE TABLE IF NOT EXISTS user_combo_decisions (
  user_id INTEGER NOT NULL,
  suggested_combo_id INTEGER NOT NULL,
  taken INTEGER NOT NULL CHECK (taken IN (0, 1)),
  updated_at_utc TEXT NOT NULL,
  stake_amount REAL,
  user_outcome TEXT CHECK (user_outcome IS NULL OR user_outcome IN ('win', 'loss', 'pending')),
  user_outcome_updated_at_utc TEXT,
  PRIMARY KEY (user_id, suggested_combo_id),
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  FOREIGN KEY (suggested_combo_id) REFERENCES suggested_combos(suggested_combo_id) ON DELETE CASCADE
);


-- Snapshot al momento de generación del pick (criterio “hechos del inicio del día”)
CREATE TABLE IF NOT EXISTS pick_baseline_snapshots (
  pick_id INTEGER PRIMARY KEY,
  captured_at_utc TEXT NOT NULL,
  baseline_json TEXT NOT NULL,
  FOREIGN KEY (pick_id) REFERENCES picks(pick_id)
);

-- Chequeos opcionales por franja / manual (señal ok vs degradada)
CREATE TABLE IF NOT EXISTS pick_signal_checks (
  check_id INTEGER PRIMARY KEY AUTOINCREMENT,
  pick_id INTEGER NOT NULL,
  slot TEXT NOT NULL,
  checked_at_utc TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ok', 'degraded', 'unknown')),
  detail_json TEXT,
  FOREIGN KEY (pick_id) REFERENCES picks(pick_id)
);

CREATE INDEX IF NOT EXISTS idx_user_pick_decisions_pick ON user_pick_decisions(pick_id);
CREATE INDEX IF NOT EXISTS idx_suggested_combos_run ON suggested_combos(daily_run_id);
CREATE INDEX IF NOT EXISTS idx_pick_signal_checks_pick ON pick_signal_checks(pick_id);


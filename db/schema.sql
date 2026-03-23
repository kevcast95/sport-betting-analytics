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
  event_id INTEGER NOT NULL,
  dataset TEXT NOT NULL, -- event|lineups|statistics|h2h|team_streaks|team_season_stats|odds_all|odds_featured
  captured_at_utc TEXT NOT NULL, -- ISO
  payload_raw TEXT NOT NULL, -- JSON
  source TEXT,
  UNIQUE(event_id, dataset, captured_at_utc)
);

CREATE TABLE IF NOT EXISTS event_features (
  feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL,
  captured_at_utc TEXT NOT NULL, -- ISO
  features_json TEXT NOT NULL, -- JSON
  processor_versions_json TEXT NOT NULL, -- JSON
  UNIQUE(event_id, captured_at_utc)
);

CREATE TABLE IF NOT EXISTS picks (
  pick_id INTEGER PRIMARY KEY AUTOINCREMENT,
  daily_run_id INTEGER NOT NULL,
  event_id INTEGER NOT NULL,
  market TEXT NOT NULL, -- e.g. 1X2
  selection TEXT NOT NULL CHECK (selection IN ('1','X','2')),
  picked_value REAL, -- decimal odds or similar
  odds_reference TEXT, -- JSON
  status TEXT NOT NULL CHECK (status IN ('pending','validated','void')),
  created_at_utc TEXT NOT NULL, -- ISO
  idempotency_key TEXT NOT NULL UNIQUE,
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


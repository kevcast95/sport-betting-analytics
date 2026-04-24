import logging
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class BT2Settings(BaseSettings):
    sportmonks_api_key: str
    theoddsapi_key: str = ""
    bt2_database_url: str
    bt2_secret_key: str = "dev-secret-change-me"
    bt2_environment: str = "development"
    # Leído desde .env vía Pydantic (no depende de os.environ; ver _require_bt2_admin).
    bt2_admin_api_key: str = ""
    # T-169 / D-06-018 — proveedor DSR en snapshot (rules | deepseek).
    bt2_dsr_provider: str = "rules"
    # Si false: no se invoca DeepSeek aunque bt2_dsr_provider=deepseek y haya clave (ahorro API + fallback SQL).
    bt2_dsr_enabled: bool = True
    deepseek_api_key: str = ""
    bt2_dsr_deepseek_base_url: str = "https://api.deepseek.com"
    bt2_dsr_deepseek_model: str = "deepseek-reasoner"
    bt2_dsr_timeout_sec: int = 120
    bt2_dsr_max_retries: int = 1
    # T-170 / D-06-019 — eventos por lote HTTP (v1-equivalente).
    bt2_dsr_batch_size: int = 15
    # T-177 — opcional: restringe pool a `bt2_leagues.id` listados (coma-separados).
    bt2_priority_league_ids: str = ""
    # Solo desarrollo: habilita POST /bt2/dev/reset-operating-day-for-tests (JWT del usuario).
    bt2_dev_operating_day_reset: bool = False

    # S6.5 — experimento SofaScore (US-OPS-003 / EJECUCION.md; staging solamente).
    bt2_sfs_experiment_enabled: bool = False
    bt2_sfs_experiment_max_events_per_run: int = 500
    bt2_sfs_http_max_rps: float = 4.0
    bt2_sfs_http_timeout_sec: int = 25
    bt2_sfs_base_url: str = "https://www.sofascore.com/api/v1"
    bt2_sfs_join_seed_json_path: str = ""  # opcional: map sportmonks_fixture_id → sofascore_event_id
    bt2_sfs_v1_sqlite_path: str = ""  # opcional bootstrap; no pipeline operativo
    # Piloto / producción: mezcla cuotas SFS (tabla bt2_provider_odds_snapshot) con SM en ds_input.
    bt2_sfs_markets_fusion_enabled: bool = False
    bt2_sfs_odds_provider_slug: str = "sofascore_experimental"
    # Tras SportMonks en `fetch_upcoming`: join + fetch SofaScore y UPSERT en bt2_provider_odds_snapshot.
    bt2_sfs_auto_ingest_enabled: bool = True
    bt2_sfs_cdm_run_id: str = "cdm_fetch_upcoming"
    # Replay / backtest admin (GET /bt2/admin/analytics/backtest-replay).
    bt2_backtest_max_span_days: int = 31
    bt2_backtest_max_events_per_day: int = 20

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


bt2_settings = BT2Settings()
logger.info("[BT2] settings loaded — env: %s", bt2_settings.bt2_environment)

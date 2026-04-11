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
    bt2_dsr_deepseek_model: str = "deepseek-chat"
    bt2_dsr_timeout_sec: int = 120
    bt2_dsr_max_retries: int = 1
    # T-170 / D-06-019 — eventos por lote HTTP (v1-equivalente).
    bt2_dsr_batch_size: int = 15
    # T-177 — opcional: restringe pool a `bt2_leagues.id` listados (coma-separados).
    bt2_priority_league_ids: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


bt2_settings = BT2Settings()
logger.info("[BT2] settings loaded — env: %s", bt2_settings.bt2_environment)

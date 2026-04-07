import logging
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class BT2Settings(BaseSettings):
    sportmonks_api_key: str
    theoddsapi_key: str = ""
    bt2_database_url: str
    bt2_secret_key: str = "dev-secret-change-me"
    bt2_environment: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


bt2_settings = BT2Settings()
logger.info("[BT2] settings loaded — env: %s", bt2_settings.bt2_environment)

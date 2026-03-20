"""
processors

Aquí vivirán los módulos que transforman el JSON crudo de SofaScore
en objetos ultra-específicos y limpios para analítica.

Regla: cada processor debe ser una función pura:
  input: dict (raw)
  output: dict (processed)
"""

from .lineups_processor import process_lineups  # noqa: F401
from .odds_all_processor import process_odds_all  # noqa: F401
from .odds_feature_processor import process_odds_feature  # noqa: F401
from .statistics_processor import process_statistics  # noqa: F401
from .validate_1x2_processor import process_validate_1x2  # noqa: F401



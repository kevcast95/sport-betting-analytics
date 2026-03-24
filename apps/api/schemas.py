from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class DailyRunOut(BaseModel):
    daily_run_id: int
    run_date: str
    sport: str
    created_at_utc: str
    status: Literal["running", "complete", "failed"]


class DailyRunPage(BaseModel):
    items: List[DailyRunOut]
    next_cursor: Optional[int] = Field(
        None,
        description="Siguiente cursor (daily_run_id): enviar como query `cursor` para la página siguiente.",
    )


class PickResultOut(BaseModel):
    validated_at_utc: str
    home_score: Optional[int]
    away_score: Optional[int]
    result_1x2: Optional[Literal["1", "X", "2"]]
    outcome: Literal["win", "loss", "pending"]
    evidence_json: Any


class PickSummary(BaseModel):
    pick_id: int
    daily_run_id: int
    event_id: int
    market: str
    selection: str
    picked_value: Optional[float]
    odds_reference: Any
    status: Literal["pending", "validated", "void"]
    created_at_utc: str
    idempotency_key: str
    result: Optional[PickResultOut]
    user_taken: Optional[bool] = Field(
        None,
        description="Si se envía user_id en el board, indica si el usuario marcó ‘tomado’.",
    )
    risk_category: Optional[str] = None
    decision_origin: Optional[str] = None
    stake_amount: Optional[float] = None
    user_outcome: Optional[Literal["win", "loss", "pending"]] = Field(
        None,
        description="Cierre manual (omitir en PATCH parcial para conservar el valor guardado).",
    )
    realized_return_cop: Optional[float] = Field(
        None,
        description="Ganancia bruta en COP persistida solo si el resultado efectivo es win.",
    )
    event_label: Optional[str] = Field(
        None, description="Partido A vs B (desde event_features del run)"
    )
    league: Optional[str] = None
    kickoff_display: Optional[str] = Field(
        None,
        description="Hora de inicio del partido en Colombia (p. ej. 18:30 · hora Colombia).",
    )
    kickoff_at_utc: Optional[str] = Field(
        None,
        description="Inicio del partido en ISO 8601 UTC (Z).",
    )
    match_state: Optional[str] = Field(
        None,
        description="Estado del partido desde event_features (not started, live, finished).",
    )
    run_date: Optional[str] = Field(
        default=None,
        description="YYYY-MM-DD del daily_run (día del análisis / listado).",
    )


class PickDetail(PickSummary):
    """Mismo shape que lista pero explícito para OpenAPI / detalle."""


class PickPage(BaseModel):
    items: List[PickSummary]
    next_cursor: Optional[int]


class PickStatusPatch(BaseModel):
    """Escritura acotada: solo void desde operaciones manuales locales."""

    status: Literal["void"]


class PickStatusPatchResponse(BaseModel):
    ok: bool
    pick_id: int
    status: str


class BacktestRunOut(BaseModel):
    backtest_run_id: int
    range_start: str
    range_end: str
    strategy_version: str
    created_at_utc: str
    metrics_json: Optional[Any]


class BacktestRunPage(BaseModel):
    items: List[BacktestRunOut]
    next_cursor: Optional[int]


class HealthOut(BaseModel):
    ok: bool
    db_path: str


# --- Tracking usuarios / combinaciones ---


class UserOut(BaseModel):
    user_id: int
    slug: str
    display_name: str
    created_at_utc: str
    bankroll_cop: Optional[float] = Field(
        None, description="Bankroll de referencia en COP (persistido en servidor)."
    )


class UserBankrollBody(BaseModel):
    bankroll_cop: Optional[float] = Field(
        None,
        description="Nuevo bankroll en COP; null borra el valor guardado.",
        ge=0,
    )


class UserCreate(BaseModel):
    slug: str
    display_name: str


class UserPickTakenBody(BaseModel):
    taken: bool
    notes: Optional[str] = None
    risk_category: Optional[
        Literal["escalonada", "segura", "balanceada", "arriesgada", "justificada"]
    ] = None
    decision_origin: Optional[Literal["analizada", "intuicion", "impulso"]] = None
    stake_amount: Optional[float] = Field(None, ge=0)
    user_outcome: Optional[Literal["win", "loss", "pending"]] = Field(
        None,
        description="Tu resultado; no enviar el campo para no modificar el cierre guardado.",
    )
    user_outcome_auto: bool = Field(
        False,
        description="Si true, quita el cierre manual (solo score/API automática).",
    )


class UserComboTakenBody(BaseModel):
    taken: bool
    stake_amount: Optional[float] = Field(None, ge=0)
    user_outcome: Optional[Literal["win", "loss", "pending"]] = Field(
        None,
        description="Cierre manual de la combinada; omitir para no cambiar el guardado.",
    )
    user_outcome_auto: bool = Field(
        False,
        description="Si true, usa solo el resultado inferido de las piernas.",
    )


class ComboLegOut(BaseModel):
    pick_id: int
    leg_order: int
    event_id: int
    market: str
    selection: str


class SuggestedComboOut(BaseModel):
    suggested_combo_id: int
    daily_run_id: int
    rank_order: int
    created_at_utc: str
    strategy_note: Optional[str]
    legs: List[ComboLegOut]
    user_taken: Optional[bool] = None
    user_stake_amount: Optional[float] = Field(
        None, description="Monto en COP registrado para esta combinada."
    )
    user_outcome: Optional[Literal["win", "loss", "pending"]] = Field(
        None, description="Cierre manual del usuario, si existe."
    )
    outcome_from_legs: Literal["win", "loss", "pending"] = Field(
        ...,
        description="Resultado lógico si todas las piernas ganan / alguna pierde / resto pendiente.",
    )
    outcome_effective: Literal["win", "loss", "pending"] = Field(
        ...,
        description="Prioriza user_outcome; si no, outcome_from_legs.",
    )


class DailyRunBoardOut(BaseModel):
    daily_run_id: int
    run_date: str
    sport: str
    status: str


class TrackingBoardOut(BaseModel):
    run: DailyRunBoardOut
    user_id: int
    picks: List[PickSummary]
    suggested_combos: List[SuggestedComboOut]


class RegenerateCombosResponse(BaseModel):
    ok: bool
    daily_run_id: int
    suggested_combo_ids: List[int]


class EnsureBaselinesResponse(BaseModel):
    ok: bool
    daily_run_id: int
    baselines_inserted: int


class SignalCheckBody(BaseModel):
    slot: str = Field(..., description="morning | afternoon | manual | otro")
    status: Literal["ok", "degraded", "unknown"]
    detail: Optional[Any] = None


class SignalCheckOut(BaseModel):
    ok: bool
    check_id: int


class DashboardPerformanceSplit(BaseModel):
    """Conteos por resultado efectivo (prioriza cierre usuario + pick_results)."""

    wins: int
    losses: int
    pending: int


class DashboardPerformanceBlock(BaseModel):
    """Todos los picks del día vs tomados vs no tomados (requiere usuario para el cruce)."""

    totals: DashboardPerformanceSplit
    taken: DashboardPerformanceSplit
    not_taken: DashboardPerformanceSplit


class DashboardSummaryBlock(BaseModel):
    run_date: str
    events_total: int = 0
    selection_passed_filters: int = 0
    selection_rejected: int = 0
    selection_selected_events: int = 0
    selection_top_reject_reason: Optional[str] = None
    selection_top_reject_reason_count: int = 0
    selection_analyzed_without_pick: int = 0
    picks_total: int
    outcome_wins: int
    outcome_losses: int
    outcome_pending: int
    picks_taken_count: int
    taken_outcome_wins: int = 0
    taken_outcome_losses: int = 0
    taken_outcome_pending: int = 0
    performance: DashboardPerformanceBlock
    bankroll_cop: Optional[float] = Field(
        None,
        description="Saldo en servidor (`users.bankroll_cop`); se ajusta con wins/loss de picks tomados.",
    )
    net_pl_estimate: Optional[float] = None
    has_stake_data: bool = False


class DashboardRecentPick(BaseModel):
    pick_id: int
    daily_run_id: int
    event_id: int
    market: str
    selection: str
    picked_value: Optional[float]
    created_at_utc: str
    outcome: Optional[Literal["win", "loss", "pending"]] = Field(
        None,
        description="Resultado efectivo (prioriza cierre manual del usuario).",
    )
    outcome_system: Optional[Literal["win", "loss", "pending"]] = Field(
        None,
        description="Solo validación automática (pick_results), si existe.",
    )
    user_outcome: Optional[Literal["win", "loss", "pending"]] = Field(
        None,
        description="Cierre declarado por el usuario, si lo hubo.",
    )
    user_taken: Optional[bool] = None
    risk_category: Optional[str] = None
    decision_origin: Optional[str] = None
    stake_amount: Optional[float] = None
    event_label: Optional[str] = None
    league: Optional[str] = None
    kickoff_display: Optional[str] = None
    kickoff_at_utc: Optional[str] = None
    match_state: Optional[str] = None
    selection_display: Optional[str] = None
    odds_reference: Optional[Any] = Field(
        None, description="Metadatos del modelo (edge, confianza, razón, etc.)"
    )


class DashboardBundleOut(BaseModel):
    summary: DashboardSummaryBlock
    recent: List[DashboardRecentPick]


class EffectivenessReportStatusOut(BaseModel):
    available: bool
    generated_at_utc: Optional[str] = None
    range_start: Optional[str] = None
    range_end: Optional[str] = None
    days: Optional[int] = None
    issued: Optional[int] = None
    settled: Optional[int] = None
    win_rate: Optional[float] = None
    roi_unit: Optional[float] = None

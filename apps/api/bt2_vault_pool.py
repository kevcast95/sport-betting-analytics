"""
US-BE-030 / D-05.2-002 + **US-BE-044 / D-06-032 (S6.2)** — slate y franjas.

Franjas (hora local del usuario, kickoff del evento) — **D-06-032**:
  mañana    [06:00, 12:00)
  tarde     [12:00, 18:00)
  noche     [18:00, 24:00)  (hasta 23:59)
  madrugada [00:00, 06:00) — overnight; fuera del flujo normal de promoción (orden al final).

Universo hacia el cómputo del día: hasta **20** candidatos valor (router recorta antes de compose).
Se persisten hasta **20** filas en `bt2_daily_picks` (orden franjas + calidad; luego el router puede
reordenar `slate_rank` para mezclar **familias de mercado**). **GET /bt2/vault/picks** devuelve
**todas** las filas persistidas (hasta 20). La **cartelera visible** (típ. 5 tarjetas) la recorta
la **UI** con `poolHardCap` / `selectVisibleFromOrderedPool` (**D-06-032**).
"""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import List, Literal, Optional, Tuple
from zoneinfo import ZoneInfo

VaultTimeBand = Literal["morning", "afternoon", "evening", "overnight"]

# Candidatos SM/CDM considerados antes de `compose_vault_daily_picks` (recorte en router).
VAULT_VALUE_POOL_UNIVERSE_MAX: int = 20
# Cartelera visible (respuesta GET /vault/picks y cupo toma 3+2).
VAULT_POOL_TARGET: int = 5
VAULT_POOL_HARD_CAP: int = 5
_MAX_PER_BAND: int = 5
_STD_SLOTS: int = 3
_PREM_SLOTS: int = 2

_BAND_ORDER: Tuple[VaultTimeBand, ...] = (
    "morning",
    "afternoon",
    "evening",
    "overnight",
)


def _minutes_since_midnight(t: time) -> int:
    return t.hour * 60 + t.minute


def time_band_from_local_time(t: time) -> VaultTimeBand:
    """
    D-06-032: 06–12 mañana, 12–18 tarde, 18–24 noche, 00–06 madrugada (overnight).
    """
    m = _minutes_since_midnight(t)
    if 6 * 60 <= m < 12 * 60:
        return "morning"
    if 12 * 60 <= m < 18 * 60:
        return "afternoon"
    if 18 * 60 <= m < 24 * 60:
        return "evening"
    return "overnight"


def kickoff_utc_to_time_band(
    kickoff_utc: Optional[datetime],
    user_tz: ZoneInfo,
) -> VaultTimeBand:
    """Sin kickoff → overnight (stock D-05.2-002 §2 hasta cierre PO)."""
    if kickoff_utc is None:
        return "overnight"
    if kickoff_utc.tzinfo is None:
        kickoff_utc = kickoff_utc.replace(tzinfo=timezone.utc)
    local = kickoff_utc.astimezone(user_tz)
    return time_band_from_local_time(local.time())


def _tier_for_slot_index(slot_in_band: int) -> Literal["standard", "premium"]:
    if slot_in_band < _STD_SLOTS:
        return "standard"
    return "premium"


def rotated_band_order(cycle_offset: int) -> Tuple[VaultTimeBand, ...]:
    """Rota el orden de barrido de franjas (0 = mañana primero, como D-06-032 base)."""
    bo = list(_BAND_ORDER)
    n = len(bo)
    k = cycle_offset % n
    return tuple(bo[k:] + bo[:k])


def compose_vault_daily_picks(
    rows: List[Tuple[int, Optional[datetime], float]],
    user_tz: ZoneInfo,
    premium_eligible_event_ids: Optional[set[int]] = None,
    *,
    band_cycle_offset: int = 0,
) -> List[Tuple[int, Literal["standard", "premium"], VaultTimeBand]]:
    """
    rows: lista (event_id, kickoff_utc, house_margin) ya ordenada por calidad
          (tier liga + house_margin como en SQL).
    Devuelve hasta VAULT_VALUE_POOL_UNIVERSE_MAX filas (event_id, access_tier, time_band)
    para persistir en DB; las primeras VAULT_POOL_HARD_CAP son la cartelera visible.

    T-178: si `premium_eligible_event_ids` no es None, solo esos event_id pueden
    recibir tier premium; el resto fuerza standard aunque el slot sea premium.

    `band_cycle_offset`: al regenerar slate, rota qué franja se prioriza primero
    (mismo universo ≤20; distinto orden 1..20 y distintos 5 visibles).
    """
    band_order = rotated_band_order(band_cycle_offset)
    # bucket por franja preservando orden de calidad global
    buckets: dict[VaultTimeBand, List[int]] = {b: [] for b in _BAND_ORDER}
    kick_by_eid: dict[int, Optional[datetime]] = {}
    band_by_eid: dict[int, VaultTimeBand] = {}
    for event_id, ko, _hm in rows:
        band = kickoff_utc_to_time_band(ko, user_tz)
        if event_id in band_by_eid:
            continue
        kick_by_eid[event_id] = ko
        band_by_eid[event_id] = band
        buckets[band].append(event_id)

    chosen: List[Tuple[int, Literal["standard", "premium"], VaultTimeBand]] = []
    chosen_ids: set[int] = set()

    def _effective_tier(eid: int, slot: int) -> Literal["standard", "premium"]:
        t = _tier_for_slot_index(slot)
        if premium_eligible_event_ids is not None and eid not in premium_eligible_event_ids:
            return "standard"
        return t

    def append_from_band(band: VaultTimeBand) -> None:
        nonlocal chosen
        slot = 0
        for eid in buckets[band]:
            if len(chosen) >= VAULT_VALUE_POOL_UNIVERSE_MAX:
                return
            if slot >= _MAX_PER_BAND:
                break
            if eid in chosen_ids:
                continue
            tier = _effective_tier(eid, slot)
            chosen.append((eid, tier, band))
            chosen_ids.add(eid)
            slot += 1

    for band in band_order:
        append_from_band(band)

    # Rellenar hacia VAULT_POOL_TARGET desde orden global si la primera pasada no alcanzó
    def global_order_ids() -> List[int]:
        out: List[int] = []
        seen: set[int] = set()
        for event_id, _ko, _hm in rows:
            if event_id not in seen:
                seen.add(event_id)
                out.append(event_id)
        return out

    fill_idx = 0
    for eid in global_order_ids():
        if len(chosen) >= VAULT_VALUE_POOL_UNIVERSE_MAX:
            break
        if eid in chosen_ids:
            continue
        band = band_by_eid.get(eid, "overnight")
        slot = fill_idx % 5
        tier: Literal["standard", "premium"] = _effective_tier(eid, slot)
        fill_idx += 1
        chosen.append((eid, tier, band))
        chosen_ids.add(eid)

    return chosen


def is_event_available_for_pick_strict(
    *,
    event_status: str,
    kickoff_utc: Optional[datetime],
    now_utc: datetime,
) -> bool:
    """
    D-05.2-001 opción A (estricto): solo `scheduled` y instante actual estrictamente
    antes del kickoff (UTC). Sin kickoff → se deja tomar si sigue scheduled (CDM).
    """
    if event_status != "scheduled":
        return False
    if kickoff_utc is None:
        return True
    if kickoff_utc.tzinfo is None:
        kickoff_utc = kickoff_utc.replace(tzinfo=timezone.utc)
    ko = kickoff_utc.astimezone(timezone.utc)
    now = now_utc if now_utc.tzinfo else now_utc.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    return now < ko

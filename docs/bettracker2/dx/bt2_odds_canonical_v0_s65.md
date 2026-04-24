# Canónico odds v0 — Sprint 06.5 Validate SFS (US-DX-005)

**Versión:** `s65-v0` (`CANONICAL_VERSION_S65` en código).

## Familias obligatorias

| Código | Origen típico SFS |
|--------|-------------------|
| `FT_1X2` | `featured` → `process_odds_feature` → `full_time_1x2` |
| `OU_GOALS_2_5` | `all` → `process_odds_all` → `extended_markets.goals_depth.over_under_2.5` |
| `BTTS` | `all` → `btts` |
| `DOUBLE_CHANCE` | `all` → `double_chance` |

## Regla featured vs all (D-06-065)

- Raw persistido por `source_scope` = `featured` | `all` separado.
- La unificación a filas comparables ocurre **solo** vía `merge_canonical_rows()` en código, con deduplicación por `(family, selection)` (1X2 prioriza `featured`; el resto prioriza `all`).

## Evento útil (D-06-066) — texto normativo

> Un evento es **útil** para este sprint si tiene **`FT_1X2` completo** y **al menos una familia core adicional completa** entre `OU_GOALS_2_5`, `BTTS`, `DOUBLE_CHANCE`.

Implementación: `is_event_useful_s65()` en `apps/api/bt2/providers/sofascore/canonical_map.py`.

## Alias proveedor SM (métricas)

Filas derivadas de `bt2_odds_snapshot` usan `source_scope = sm_bt2_odds` (no es raw SFS; es agregado CDM ya persistido).

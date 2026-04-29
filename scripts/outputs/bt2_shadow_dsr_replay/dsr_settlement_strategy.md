# Estrategia de settlement — baseline DSR native (shadow)

Generado: `2026-04-28T23:27:32.351747+00:00`  
Ámbito: `run_family=shadow_dsr_replay_native`, `selection_source=dsr_api_only` (no productivo).

## 1. Niveles de verdad (política operativa)

| Nivel | Definición | Uso |
|-------|------------|-----|
| **Cierre oficial** | `bt2_events` (CDM local) con `result_home`/`result_away` y estado coherente con final; o verificación SM con HTTP 200 y `sm_has_ft_score` tras merge idéntico al job `bt2_shadow_evaluate_performance`. | Única base para `hit`/`miss`/`void` en eval shadow persistida. |
| **Resultado visible no oficial** | SM (o local) con FT en UI de diagnóstico pero sin pasar reglas de consistencia (p. ej. contradicción local vs SM). | Mostrar como “preliminar” en auditoría; no mover `eval_status` sin regla. |
| **Pending recheck** | `eval_status=pending_result` y merge simulado aún sin par FT; o kickoff en ventana natural. | Job diario: re-ejecutar evaluador con fallback SM; escalar tras N días. |
| **Revisión manual necesaria** | Contradicción local vs SM; `bt2_event_id` NULL; API SM con error de plan/suscripción. | Lista corta; decisión documentada (qué fuente manda y por qué). |
| **Cierre manual auditado** | Override explícito en herramienta interna con log (usuario, timestamp, motivo, fuente). | Solo si APIs y CDM no convergen y el partido es inequívoco en fuente externa puntual. |

## 2. Aterrizaje a esta auditoría (N=215 pending en instantánea)

**Diagnóstico causal (DB antes del recheck):**

| Bloque | N | Explicación |
|--------|---|-------------|
| Eval inicial sin paso H2H | 186 | `truth_source=toa_payload_only_v1`: picks persistidos tras el replay native sin ejecutar el merge CDM+SM del script de evaluación. |
| CDM incompleto tras eval H2H | 29 | `truth_source=bt2_events_cdm_v1`: el evaluador ya miró CDM pero sin marcador; SM sí podía aportar FT. |

**Clasificación “geográfica” en CSV (`root_cause_distribution_at_audit`):** 186 `bt2_event_id` NULL → “falta de enlace limpio”; 29 con enlace CDM pero sin goles → “sin marcador final en fuente local”.

**Ejecutado después de la auditoría (solo shadow):** `scripts/bt2_shadow_evaluate_performance.py --run-key shadow-dsr-native-full-20260428-214014` → **pending_result=0**, **259 scored**, **134 hit / 125 miss**. Detalle en `dsr_pending_summary.json` → `after_shadow_evaluate_performance`.

- **Cierre automático seguro (shadow)**: el comando anterior; no cambia T-60 ni productión; solo `bt2_shadow_pick_eval`.
- **CSV `dsr_pending_audit.csv`**: instantánea **antes** de esa ejecución (215 filas útiles para RCA).

## 3. Qué no relajar

- No tratar `pending` como miss ni hit.
- No usar solo “estado” sin par de goles para 1X2 H2H.
- No aceptar SM si contradice local salvo regla explícita de precedencia documentada.

## 4. Recheck (diseño ejecutable)

1. **Fin de día**: cron/dev manual — `bt2_shadow_evaluate_performance.py` con `--run-key` del native full.
2. **Histórico**: mismos fixtures con `kickoff_utc` > 48h y aún pending → revisar `sm_error_message` (suscripción) vs datos.
3. **Fallback SM**: ya implementado en el evaluador; la deuda es principalmente completitud CDM y límites del plan SM.

## 5. Control SportMonks vs local (muestra scored)

- Filas en `dsr_sportmonks_historical_reliability_check.csv`: **16** (8 hit + 8 miss máx).
- Acuerdo local vs SM (fresh): **coinciden=16, discordancia=0, sin comparación posible=0**.

---

Documento vivo; el CSV `dsr_pending_audit.csv` es la fuente detallada por pick.

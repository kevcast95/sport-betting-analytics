# Sprint 07 — Planificación (borrador)

> **Estado:** placeholder para no mezclar con Sprint 06.  
> **Fuente:** [`../sprint-05/DECISIONES.md`](../sprint-05/DECISIONES.md) **D-05-001** y propuesta producto (parlays, diagnóstico, D-04-001).

## Objetivo orientativo

- **Parlays:** tablas `bt2_parlays`, `bt2_parlay_legs`, liquidación tipo **AND**, límite **2 parlays sugeridos/día** (1×2 + 1×3), costes DP **−25 / −50**, milestone desbloqueo permanente (**D-04-012**, **D-04-013**).
- **DSR** propone combinaciones; Python valida y persiste.
- **Diagnóstico:** scoring / recalibración automática con historial **`bt2_user_diagnostics`** (excluido de US-BE-016 / S4).
- **D-04-001:** `unit_value_cop` por sesión para bankroll COP fiel al operador.

## Próximo paso

Al cerrar **Sprint 06**, crear `sprint-07/US.md`, `TASKS.md`, `DECISIONES.md` y continuar numeración US/tareas desde el último id S6.

## Deuda arrastrada desde Sprint 06 (coordinación PO)

- **US-DX-002 — T-153:** catálogo `MarketCanonical` en DX (`bt2_dx_constants.py` + `bt2Types.ts`) y documentación DECISIONES; cierre depende de acuerdo FE/PO.
- **US-DX-002 — T-155:** `operatorProfile` + OpenAPI (`label_es`, alias camelCase, coherencia `reason` ledger); puede cerrarse en S7 sin bloquear **T-169** ya entregado.

*Motivo:* el cierre BE **T-169** no exige bump de `contractVersion`; el **merge masivo** de FE que asuma contrato “final” sigue gobernado por hito DX (**D-06-017**).

---

*Última actualización: 2026-04-08 — deuda DX T-153/T-155; stub resto PLAN.*

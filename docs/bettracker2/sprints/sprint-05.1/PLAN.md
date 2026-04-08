# Sprint 05.1 — Refinement (post S5)

> **Tipo:** refinement corto sobre **Sprint 05** cerrado o en cierre formal.  
> **Primer tema:** **RFB-09** — desbloqueo premium **separado** de “tomar” el pick ([`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md)).

## Objetivo (05.1)

Corregir el comportamiento en el que **deslizar el desbloqueo premium** dispara de inmediato **`POST /bt2/picks`** y la UI muestra **“En juego”**, cuando el producto exige: **primero desbloquear (−50 DP)** y **después** el usuario **elige tomar** el pick (compromiso operativo).

## Alcance explícito

- **Incluye:** **RFB-09** — contrato y flujo **BE + FE** desbloqueo premium vs tomar pick (**US-BE-029**, **US-FE-040**).
- **Incluye:** **RFB-01** + **RFB-10** — cabecera V2 unificada, sin «Actualizado ahora» decorativo, ayuda «Cómo funciona» a la izquierda (**US-FE-043**, **D-05.1-003**).
- **Incluye:** **RFB-07** + **RFB-08** — bóveda: opacidad/tag tras inicio; premium bloqueado solo datos mínimos + cuota (**US-FE-044**, **D-05.1-004**, **D-05.1-005**).
- **Incluye:** **RFB-11** … **RFB-13** — ledger/rendimiento: nombres y métricas honestas (**US-FE-045**, **D-05.1-006** … **D-05.1-008**, **T-180–T-182**).
- **Incluye:** **RFB-02**, **RFB-03**, **RFB-04**, **RFB-14**, **RFB-15** — Santuario, glosario, sidebar DP, doble fetch (**US-FE-046 … US-FE-049**, **D-05.1-009 … D-05.1-013**, **T-183–T-187**).
- **Siguiente oleada:** **RFB-05**, **RFB-06** — backlog **[`../sprint-05.2/`](../sprint-05.2/PLAN.md)** (**US-BE-030/031**, **US-FE-050/051**, **T-188+**, [`EJECUCION.md`](../sprint-05.2/EJECUCION.md)); parte fuerte “refresh/regeneración” sigue **D-05.2-003** / **S6+**.
- **Excluye:** narrativa DSR en bóveda (**Sprint 06**) salvo lo ya acotado arriba.

## Numeración US / conflicto con Sprint 06

- **US-FE-040** en esta carpeta = **RFB-09** (bóveda premium). En S6, la bóveda **DSR** quedó renumerada a **US-FE-052** (ver [`../sprint-06/US.md`](../sprint-06/US.md)).
- **US-FE-043** en **05.1** = shell / cabecera (**RFB-01**, **RFB-10**). En Sprint 06, Analytics y mercados canónicos quedaron en **US-FE-053** / **US-FE-054** (ver [`../sprint-06/US.md`](../sprint-06/US.md)).
- **US-FE-044** en **05.1** = `PickCard` / bóveda (**RFB-07**, **RFB-08**). Comprobar que ningún borrador S6 reclame el id **044** antes de ejecutar.
- **US-FE-045** en **05.1** = ledger + rendimiento (**RFB-11**, **RFB-12**, **RFB-13**). Renumerar cualquier borrador S6 que use **045** antes de ejecutar S6.
- **US-FE-046** … **US-FE-049** en **05.1** = **RFB-02/03**, **RFB-04**, **RFB-14**, **RFB-15**. **US-FE-050** … **US-FE-051** = **RFB-05/06** en **[`../sprint-05.2/US.md`](../sprint-05.2/US.md)**. **Sprint 06** FE DSR/analytics usa **US-FE-052+** (ver [`../sprint-06/US.md`](../sprint-06/US.md)).

## Ejecución (orden BE / FE)

**Un solo handoff para todos:** **[`EJECUCION.md`](./EJECUCION.md)** — BE ejecuta **Bloque 1**, FE **Bloque 2** (US, **T-170+**, orden).

## Archivos

| Archivo | Uso |
|---------|-----|
| [`US.md`](./US.md) | **US-BE-029**, **US-FE-040**, **US-FE-043** … **US-FE-049**, **US-DX-001-R1** (opcional). **Nota BE:** el antiguo **US-BE-024** del S5 quedó fusionado en **US-BE-018 §9**; refinement BE = **US-BE-029**. |
| [`TASKS.md`](./TASKS.md) | **T-170+** (tras **T-169** del S5). |
| [`DECISIONES.md`](./DECISIONES.md) | **D-05.1-001 … D-05.1-013**. |
| [`EJECUCION.md`](./EJECUCION.md) | Mismo archivo para BE y FE; cada uno su bloque. |
| [`AUDITORIA_ESTADO.md`](./AUDITORIA_ESTADO.md) | Snapshot código vs backlog (¿listo para S6?). |
| [`PENDIENTES_EJECUCION.md`](./PENDIENTES_EJECUCION.md) | Orden concreto para cerrar **T-175, T-184, T-176, T-187** y checklists. |

---

*Última actualización: 2026-04-09 — enlace **Sprint 05.2** (RFB-05/06) + numeración **US-FE-052+** en S6.*

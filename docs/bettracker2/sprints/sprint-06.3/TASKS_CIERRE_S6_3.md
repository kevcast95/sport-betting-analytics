# Sprint 06.3 — TASKS_CIERRE

> Cierre restante de S6.3 tras implementación del slice principal de Fase 1.
> Numeración: continúa desde T-245 (S6.3). Rango propuesto de cierre: T-246 … T-257.
> Base vigente del sprint: `TASKS.md`, `US.md`, `EJECUCION.md`, `EJECUCION_UI_FASE1.md`.
> Documentos de cierre: `DECISIONES_CIERRE_S6_3.md`, `US_CIERRE_S6_3.md`, `HANDOFF_CIERRE_S6_3.md`.
> Foco: evidencia operativa real de Fase 1 + mínimo paralelo de F2 dentro de S6.3 + cierre documental honesto.

* * *

## Apto 100% para ejecución (Definition of Ready)

✓ Qué se confirma | Quién (típico)

- [ ] `CIERRE_RESTANTE_S6_3.md` leído y entendido como documento base del cierre restante. | PO / TL
- [ ] `DECISIONES_CIERRE_S6_3.md` aprobado antes de ejecutar tasks operativas de cierre. | PO / TL
- [ ] La implementación principal de Fase 1 ya está desplegada o accesible en el entorno donde se validará. | TL / BE
- [ ] Se definió la ventana real a usar para evidencia (`operating_day_key`, día o rango). | TL / BE
- [ ] Existe acceso a BD / logs / ruta admin para levantar evidencia real. | TL / BE / FE

* * *

## Checklist de cobertura cierre S6.3

Capa / decisión | US | Tareas
--- | --- | ---
Evidencia operativa real del loop | US-BE-053 | T-246–T-248
Evidencia operativa real de elegibilidad/auditoría | US-BE-054 | T-249–T-251
Validación mínima paralelo F2 | US-BE-055 | T-252–T-253
Validación admin con datos reales | US-FE-062 | T-254–T-255
Cierre documental del sprint | transversal | T-256–T-257

* * *

## US-BE-053

- [x] **T-246 (US-BE-053)** — Validar en entorno real que migraciones/tablas/código del loop oficial estén efectivamente disponibles para operar sobre picks reales.
- [x] **T-247 (US-BE-053)** — Ejecutar job o backfill de official evaluation sobre uno o más `operating_day_key` reales y confirmar filas en `bt2_pick_official_evaluation`.
- [x] **T-248 (US-BE-053)** — Documentar evidencia del loop con picks reales: SQL, salida de job, subconjunto procesado y estados observados (`pending_result`, evaluados si aplica).

* * *

## US-BE-054

- [x] **T-249 (US-BE-054)** — Ejecutar auditoría de elegibilidad sobre eventos reales del día o ventana validada y confirmar filas en `bt2_pool_eligibility_audit`.
- [x] **T-250 (US-BE-054)** — Validar endpoint summary/admin contra BD con datos reales no vacíos; confirmar coverage, auditoría reciente y consistencia básica.
- [x] **T-251 (US-BE-054)** — Documentar evidencia de elegibilidad/auditoría real: SQL, coverage observado, motivos de descarte y desaparición del patrón dominante “sin auditoría reciente”, si aplica.

* * *

## US-BE-055

- [x] **T-252 (US-BE-055)** — Medir coverage real por liga y mercado piloto usando la ventana validada, incluyendo descarte por causa principal.
- [x] **T-253 (US-BE-055)** — Emitir conclusión corta de validación: la regla mínima actual se sostiene o requiere un único ajuste puntual; si requiere ajuste, dejar nota/decisión corta enlazada.

* * *

## US-FE-062

- [x] **T-254 (US-FE-062)** — Validar `/v2/admin/fase1-operational` con datos reales no vacíos y revisar consistencia visual con summary/backend. *(FE: checklist T-254 + `operatingDayKey` de respuesta API en `AdminFase1OperationalPage.tsx`; QA con BD en entorno real sigue siendo responsabilidad de operación.)*
- [x] **T-255 (US-FE-062)** — Capturar evidencia funcional del admin: candidatos, auditoría reciente, evaluación oficial, estados visibles y consistencia con BD/endpoint. *(Procedimiento y referencia de captura en `EJECUCION_UI_FASE1.md` § US-FE-062.)*

* * *

## Gobernanza y cierre documental

- [x] **T-256 (S6.3 transversal)** — Actualizar `EJECUCION.md` con evidencia real del loop, de elegibilidad/auditoría, de la vista admin y de la validación mínima del paralelo F2. *(“Vista admin” = endpoint `fase1-operational-summary` validado vs BD; captura UI en T-255.)*
- [x] **T-257 (S6.3 transversal)** — Cierre **BE + evidencia operativa** reflejado en este archivo y en [`EJECUCION.md`](./EJECUCION.md). **FE:** T-254–T-255 cubiertas en código + `EJECUCION_UI_FASE1.md`; captura de pantalla en entorno real opcional según PO.

* * *

## Check cierre real S6.3

- [x] Existe evidencia de loop oficial para un subconjunto real de picks.
- [x] Existe evidencia de auditoría de elegibilidad para eventos reales del día o ventana analizada.
- [x] La vista admin de Fase 1 muestra datos operativos no vacíos y consistentes con BD. *(Checklist + clave de día en UI; captura real T-255 en entorno operativo según `EJECUCION_UI_FASE1.md`.)*
- [x] La regla mínima de elegibilidad fue validada con datos reales y, si hizo falta, se emitió una decisión mínima adicional.
- [x] `EJECUCION.md` y `TASKS_CIERRE_S6_3.md` reflejan el cierre real del pendiente restante (BE).

* * *

Creación: 2026-04-14 — tasks finales para cierre real de S6.3.
# Sprint 05 — Planificación (borrador)

> **Estado:** plan abierto. Completar con fechas, owner y priorización tras acuerdo PM + BE + FE.  
> **Sprint 04 cerrado** con referencia en [`../sprint-04/US.md`](../sprint-04/US.md) (estado Done).

## 1. Cómo conviene trabajarlo (proceso)

1. **Conjunto (producto / BA / PM):** definir en este archivo o en `US.md` del sprint **objetivos del Sprint 05**, temas, y **límites** (qué no entra).
2. **Frontend (US-FE):** redactar o refinar US-FE en `sprints/sprint-05/US.md` cuando exista + `TASKS.md` con `T-### (US-FE-###)`.
3. **Backend (US-BE):** el rol BE **no** “va detrás” en silencio: las mismas conversaciones deben producir **US-BE** y tareas en el mismo `US.md` / `TASKS.md` del sprint (o handoff explícito con contrato OpenAPI / US-DX).
4. **Contratos (US-DX):** si DS en modelo de predicción o nuevos endpoints tocan payload compartido, una **US-DX** o sección de contrato **antes** de que FE asuma campos.

En resumen: **sí, se sigue manejando en conjunto**; después de fijar el “qué” del sprint, **BE define e incluye sus US/tareas en el mismo paquete de sprint**, no en un documento aparte desconectado.

## 2. Bolsa de temas (heredados + nuevos)

### 2.1 Producto / FE (pendientes explícitos)

| Tema | Origen | Nota |
|------|--------|------|
| UI `GET /bt2/user/dp-ledger` | T-124 aplazado | Trazabilidad de movimientos DP para el operador. |
| Hidratar ledger y métricas V2 desde `GET /bt2/picks` | Deuda V2 | Fuente de verdad servidor para libro mayor, rendimiento, cierre del día. |
| Estados de pick: “seleccionado / tomado / abierto” | Gap UX bóveda + liquidación | Compromiso explícito antes de liquidar; alinear con `POST /bt2/picks` en estándar si aplica. |
| Take premium → movimiento en `bt2_dp_ledger` | Auditoría / coherencia | Hoy parcialmente solo en cliente; cerrar con BE. |
| Penalizaciones gracia (−50 / −25) persistidas | `useSessionStore` vs BD | Ledger servidor como única verdad. |
| Resumen diario (ROI/P/L/stake) endpoint o agregación | `DailyReviewPage` | Opcional score “disciplina del día” si se define regla de negocio. |

### 2.2 Backend / CDM / modelo (lo que comentaste con BE)

| Tema | Nota |
|------|------|
| **Integrar “DS” (Discipline Score / señal conductual) en el modelo de predicción** | Requiere **definición conjunta**: qué es DS numéricamente, ventana temporal, frío vs caliente, y si es *feature* de entrenamiento, *post-proceso* de ranking, o *gating* de elegibilidad. Documentar en `DECISIONES.md` y una **US-BE** + posible job/pipeline. |
| **Scheduler** job `fetch_upcoming` (Sprint 04 dejó ejecución manual) | Operación recurrente; encaja en Sprint 05 u OPS. |
| Parlays / decisiones D-04-012 / 013 | Si el producto las prioriza, US dedicadas. |

## 3. Próximos pasos concretos

- [ ] Copiar/adaptar plantilla de [`../01_CONTRATO_US.md`](../../01_CONTRATO_US.md) en **`sprint-05/US.md`** (vacío o con US borrador).
- [ ] Crear **`sprint-05/TASKS.md`** con numeración a partir del último `T-###` global acordado.
- [ ] Sesión conjunta: **priorizar** entre “DS en modelo” vs “cerrar deuda V2 API-first” (suelen competir por capacidad BE).
- [ ] Registrar **decisión de priorización** en `sprint-05/DECISIONES.md` (o primeras entradas).

---

*Última actualización: 2026-04-04 — cierre Sprint 04 / apertura plan Sprint 05.*

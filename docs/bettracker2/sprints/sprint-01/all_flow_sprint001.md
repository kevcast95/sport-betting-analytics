# all_flow_sprint001.md — Protocolo de flujo maestro (Sprint 01)

> **Fuente de verdad:** Orquesta el **user journey**, el **flujo de datos** entre US-FE y el **orden de ejecución de tareas** (`TASKS.md`) para el agente desarrollador en Cursor.  
> **Estado (2026-04-04):** **Sprint 01 frontend cerrado** — **T-001 … T-059** implementadas en `apps/web` (incl. **US-FE-024** / Bloque 12). Stub **US-BE-001** (**T-060 … T-062**) en `apps/api`. **Backlog producto/ops:** ver §6 **Sprint 02**. Detalle en [`US.md`](./US.md), [`DECISIONES.md`](./DECISIONES.md), [`TASKS.md`](./TASKS.md), [`QA_CHECKLIST.md`](./QA_CHECKLIST.md), [`../../HANDOFF_BA_PM_BACKEND.md`](../../HANDOFF_BA_PM_BACKEND.md).

---

## 1. Ciclo de vida del operador (user journey)

Tres fases lógicas; los **guards** y Zustand deben respetar este orden: **Auth → Contrato → Diagnóstico → Búnker** (sin atajos por URL).

### Fase A: Onboarding y blindaje (setup)

| US | Rol |
|----|-----|
| **US-FE-001** | Bunker Gate: auth mock, contrato de disciplina (3 axiomas), layout base. |
| **US-FE-005** | The Mirror: diagnóstico situacional, `OperatorProfile`, `systemIntegrity`. |
| **US-FE-002** | Treasury: bankroll + stake unit (COP). |
| **US-FE-011** | Cierre **fase A** (copy único + animación sobria + **abono único de DP**) y **fase B** (tour economía DP: picks abiertos vs premium, ganar/gastar, día calendario). *Dispara tras Treasury confirmado.* |

### Fase B: Operativa y santuario (bucle diario)

| US | Rol |
|----|-----|
| **US-FE-004** | Santuario: aterrizaje por defecto; salud / snapshot. |
| **US-FE-003** | La Bóveda: picks CDM, desbloqueo con DP; **US-FE-023** maqueta **abiertos vs premium** en mock. |
| **US-FE-006** | Settlement: liquidación + reflexión; +25 DP (modo confianza MVP). |
| **US-FE-013** | *[Improvement]* Trazabilidad **modo confianza** vs **verificado** (vNext); copy y constante `trust` en UI. |
| **US-FE-007** | After-Action Review: reconciliación, cierre de estación, bloqueo operativo. |
| **US-FE-012** | **Día calendario** (TZ usuario), detección de pendientes del día anterior, **gracia 24 h**, auto-cierre donde aplique, consecuencias. |
| **US-FE-014** | *[Cambio]* Coherencia **estación / `stationLockedUntilIso` / bóveda** con `operatingDayKey` y US-FE-012. |

### Fase C: Memoria y evolución (analytics)

| US | Rol |
|----|-----|
| **US-FE-008** | Strategic Ledger. |
| **US-FE-009** | Strategy & Performance. |
| **US-FE-010** | Elite Progression / perfil. |

**Contratos (handoff):** **US-DX-001** (stub) — economía conductual, `operatingDayKey`, `accessTier` / `unlockCostDp`, `settlementVerificationMode`. Sin API real en este sprint.

### Refinamientos de producto (no cambian el orden del journey)

| US | Rol |
|----|-----|
| **US-FE-015** | Cierre fase A: micro-celebración +250 DP (`OnboardingConfettiBurst`), copy de logro. |
| **US-FE-016** | Tours por ruta: primera visita + ayuda; **piloto** Santuario + Bóveda. |
| **US-FE-017** | Contrato: sin leyenda de token ficticio (`DisciplineContract`). |
| **US-FE-018** | Diagnóstico: integridad en %, estado en español, DP coherente en preview. |
| **US-FE-019** | **+90 %:** español en `/v2/*` + patrón *métrica + línea humana* (`04`). |
| **US-FE-020** | **+90 %:** auditoría semántica de color (equity vs DP vs warning). |
| **US-FE-021** | **+90 %:** extensión tours — lote A (Liquidación, Cierre del día); lote B (Ledger, Rendimiento, Perfil, Ajustes). |
| **US-FE-022** | Liquidación: evento local/visitante, mercado en ES, cuota sugerida vs cuota casa, copy “modelo/sistema” (ref. **US-FE-006**). |
| **US-FE-023** | Bóveda: mock **6–8** picks, **3–4 abiertos** + **2–3 premium**; preview tarjeta = evento + mercado ES (ref. **US-FE-003**). |
| **US-FE-024** | Liquidación/bóveda: rótulo **Mercado** + **`selectionSummaryEs`** (línea de apuesta en ES). |

---

## 2. Reconciliación de datos (data flow)

| Módulo | Emite (efecto) | Depende de |
|--------|----------------|------------|
| US-FE-005 | `systemIntegrity`, perfil | `hasAcceptedContract` |
| US-FE-002 / 011 | DP onboarding único, flags tour | Treasury confirmado; ver [`DECISIONES.md`](./DECISIONES.md) |
| US-FE-012 | `operatingDayKey`, gracia, penalizaciones | TZ usuario; reloj (MVP local) |
| US-FE-006 / 013 / **022** | PnL, +25 DP, reflexión; modo `trust`; cuota casa vs sugerida (022) | Pick activo desde **US-FE-003**; CDM mock ampliado |
| US-FE-007 / 014 | `isStationLocked`, reconciliación | Liquidaciones; coherencia con **US-FE-012** |
| US-FE-008 | Ledger | Datos persistidos post-**US-FE-006** |
| US-FE-009 | Métricas, equity | `ledger` / stores derivados |
| US-FE-010 | Rango, recalibración | DP acumulado, ledger |

---

## 3. Roadmap de ejecución para el desarrollador (orden + validación)

Ejecutar por **bloques**; dentro de cada bloque el orden T-xxx es el recomendado. Tras cada bloque, **validar** antes de abrir el siguiente.

### Bloque 0 — Sprint 01 FE completo (regresión rápida)

| Tareas | Estado |
|--------|--------|
| T-001 … T-059 | Marcadas **[x]** en [`TASKS.md`](./TASKS.md) (2026-04): incluye +90 % (T-051–055), liquidación/bóveda CDM (T-056–058), mercado + selección (T-059, **US-FE-024**). |

**Validar:** si tocas stores o guards: login mock → contrato → diagnóstico → Treasury → onboarding → Santuario / Bóveda → **Settlement** → Daily review → Ledger / Performance / Profile / Settings (tours). `npm test` en `apps/web` y smoke en `/v2/*`.

---

### Bloque 1 — Diagnóstico y guards (US-FE-005) — hecho en repo

| Orden | Tarea |
|-------|--------|
| 1 | T-016 |
| 2 | T-017 |
| 3 | T-018 |
| 4 | T-019 |
| 5 | T-020 |

**Validar (regresión):** flujo `/v2/diagnostic` en foco; auto-avance ~800 ms; preview integridad/perfil; guard redirige a diagnóstico si falta; al terminar, acceso a Santuario. Criterios en **US-FE-005** §6.

---

### Bloque 2 — Onboarding economía (US-FE-011) — hecho en repo

| Orden | Tarea |
|-------|--------|
| 1 | T-041 |
| 2 | T-042 |
| 3 | T-047 *(US-FE-015: confeti + copy logro +250)* |

**Validar (regresión):** tras primera confirmación de Treasury, cierre fase A (copy único + DP único + celebración acotada); tour fase B en español. Criterios **US-FE-011**, **US-FE-015**.

*Histórico:* Puede solaparse en tiempo con Bloque 3 si el equipo paraleliza; el tour asume diagnóstico ya completado (**T-020**).

---

### Bloque 3 — Liquidación (US-FE-006) + improvement (US-FE-013) — hecho en repo

| Orden | Tarea | Nota |
|-------|--------|------|
| 1 | T-021 | Hecho |
| 2 | T-022 | Hecho |
| 3 | T-023 | Hecho |
| 4 | T-024 | Hecho |
| 5 | T-045 | Hecho |

**Validar (regresión):** `/v2/settlement/:pickId`; reflexión mínima; PnL y bankroll; +25 DP; `settlementVerificationMode: 'trust'` y copy modo confianza. Criterios **US-FE-006** y **US-FE-013**.

---

### Bloque 4 — Cierre de estación — primera pasada (US-FE-007) — hecho en repo

| Orden | Tarea |
|-------|--------|
| 1 | T-025 |
| 2 | T-026 |
| 3 | T-027 |
| 4 | T-028 |

**Validar (regresión):** `/v2/daily-review`; reconciliación; bloqueo bóveda post-cierre. Criterios **US-FE-007** §6.

---

### Bloque 5 — Día calendario y gracia (US-FE-012)

| Orden | Tarea |
|-------|--------|
| 1 | T-043 |
| 2 | T-044 |

**Validar:** `operatingDayKey` coherente con TZ; aviso día anterior pendiente; gracia 24 h; consecuencias tras gracia según `DECISIONES.md`; logs `[BT2]`. Criterios **US-FE-012** §6.

---

### Bloque 6 — Coherencia locks vs día (US-FE-014)

| Orden | Tarea |
|-------|--------|
| 1 | T-046 |

**Validar:** `stationLockedUntilIso` y acceso a bóveda **no contradicen** US-FE-012 ni `DECISIONES.md`; copy en español sin mensajes mixtos. Criterios **US-FE-014** §6. **Dependencia:** Bloque 5 estable o en la misma PR coordinada.

---

### Bloque 7 — Ledger, rendimiento, perfil (US-FE-008 … 010) — hecho en repo

| Orden | Tareas |
|-------|--------|
| 1 | T-029 … T-032 |
| 2 | T-033 … T-036 |
| 3 | T-037 … T-040 |

**Validar (regresión):** cada US §6 y DoD en `US.md`.

---

### Bloque 8 — Tours piloto + contrato/diagnóstico (US-FE-016 … 018) — hecho en repo

| Orden | Tarea | US |
|-------|--------|-----|
| 1 | T-048 | US-FE-016 — `ViewTourModal`, Santuario + Bóveda |
| 2 | T-049 | US-FE-017 — contrato sin token ficticio |
| 3 | T-050 | US-FE-018 — diagnóstico legible |

**Validar (regresión):** primera visita y botón de ayuda en Santuario/Bóveda; modal contrato sin `SS-VAULT-*`; diagnóstico con % integridad y etiquetas de estado en español. Tests `apps/web` en verde.

---

### Bloque 9 — Plan +90 % identidad (US-FE-019 … 021) — hecho en repo

| Orden | Tarea | US |
|-------|--------|-----|
| 1 | T-051 | US-FE-019 |
| 2 | T-052 | US-FE-019 |
| 3 | T-053 | US-FE-020 |
| 4 | T-054 | US-FE-021 |
| 5 | T-055 | US-FE-021 |

**Validar (regresión):** checklist [`QA_CHECKLIST.md`](./QA_CHECKLIST.md) Bloque 9 (marcado en cierre 2026-04-04).

---

### Bloque 10 — Liquidación emulación casa (US-FE-022) — hecho en repo

| Orden | Tarea |
|-------|--------|
| 1 | T-056 |
| 2 | T-057 |

**Validar (regresión):** [`QA_CHECKLIST.md`](./QA_CHECKLIST.md) Bloque 10; DoD **US-FE-022** en [`US.md`](./US.md).

---

### Bloque 11 — Bóveda demo abierta/premium (US-FE-023) — hecho en repo

| Orden | Tarea |
|-------|--------|
| 1 | T-058 |

**Validar (regresión):** QA Bloque 11; DoD **US-FE-023**.

---

### Bloque 12 — Mercado explícito y selección (US-FE-024) — **cerrado**

| Orden | Tarea | Validar |
|-------|--------|---------|
| 1 | **T-059** | `SettlementPage`: label **«Mercado»** visible; **`selectionSummaryEs`** en CDM y en UI; `PickCard` alineado; tests verdes; QA Bloque 12. |

**Cierre 2026-04-04:** T-059 **[x]**; DoD **US-FE-024**; [`QA_CHECKLIST.md`](./QA_CHECKLIST.md) Bloque 12 marcado.

---

## 4. Reglas transversas (siempre)

1. **Stores primero** cuando el bloque introduzca estado nuevo compartido (p. ej. día operativo antes de solo UI).
2. **Refs:** `docs/bettracker2/sprints/sprint-01/refs/` — portar tokens; **sin CDN ni Material** en runtime.
3. **Identidad:** [`04_IDENTIDAD_VISUAL_UI.md`](../../04_IDENTIDAD_VISUAL_UI.md) (Zurich Calm); copy [`00_IDENTIDAD_PROYECTO.md`](../../00_IDENTIDAD_PROYECTO.md) (**español** en UI).
4. **Tipografía:** números, fechas, IDs en **Geist Mono**.
5. **Traza:** prefijo **`[BT2]`** en logs acordados en US.
6. **Cierre de US “madre”:** enmiendas posteriores viven en **US-FE-011 … 024** (y siguientes refinements) con referencias cruzadas en `US.md`; no reabrir texto de 006/007 sin nueva US.

---

## 5. Cierre Sprint 01 — frontend

- [x] `TASKS.md`: **T-001 … T-059** **[x]** alineadas a US-FE.
- [x] **US-FE-024** verificada; liquidación + bóveda + ledger.
- [x] Sin nombres de proveedor en payloads V2; CDM / mocks limpios.
- [x] `DECISIONES.md`, `US.md`, `QA_CHECKLIST.md` y handoff backend actualizados.
- [ ] **Plan de rollback operativo** — pendiente **Sprint 02 / US-OPS** (no bloquea cierre documental FE).

---

## 6. Sprint 02 — líneas sugeridas (fuera de Sprint 01)

Trabajo **no** incluido en el cierre anterior; priorizar en `sprints/sprint-02/` cuando exista carpeta.

1. **Rollback / feature flags / despliegue** (US-OPS o equivalente).
2. **Consumo FE** de `GET /bt2/*` (o API definitiva) y fuente única de verdad vs `vaultMockPicks`.
3. **Persistencia backend** usuario, ledger servidor, auth real según roadmap.
4. **T-039** (recalibración funcional cuando existan contadores reales).
5. **Modo `verified`** liquidación + jobs resultado canónico (US-BE + US-DX).
6. **E2E** o checklist PO firmado en CI (si el equipo lo adopta).
7. Ajuste fino de copy QA vs orden de líneas en **PickCard** (solo editorial si se desea igualar checklist literal).

**Handoff para BA/PM backend:** [`../../HANDOFF_BA_PM_BACKEND.md`](../../HANDOFF_BA_PM_BACKEND.md).

---

*Última actualización: Sprint 01 FE **cerrado** (T-001 … T-059, 2026-04-04).*

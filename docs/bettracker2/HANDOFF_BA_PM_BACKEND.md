# Handoff: contexto BetTracker 2.0 para BA/PM Backend

**Audiencia:** agente o persona en rol **Business Analyst / Product Owner Backend** (y arquitecto API), tras el **cierre del Sprint 01 frontend** documentado en este repo.

**Fecha de cierre FE (documental):** 2026-04-04.

**Alcance de este documento:** contexto de producto, identidad, documentación canónica, **qué construyó el FE en V2**, **qué datos y contratos espera** el cliente cuando sustituya mocks, y **backlog sugerido para Sprint 02** (sin ejecutar aquí).

---

## 1. Qué cerró el Sprint 01 (frontend)

- **Tareas:** `docs/bettracker2/sprints/sprint-01/TASKS.md` — **T-001 … T-059** (US-FE-001 … US-FE-024) marcadas **[x]** para el trabajo en `apps/web`.
- **QA:** `docs/bettracker2/sprints/sprint-01/QA_CHECKLIST.md` — actualizado con **auditoría estática + tests** (`apps/web`: **65 tests** en verde al cierre).
- **Fuera del mandato FE pero en el mismo repo:** **US-BE-001** (T-060–T-062): stub HTTP **`/bt2/*`** en `apps/api` — ver §6.

El **plan de rollback operativo** (despliegue / feature flags / reversión de datos) **no** está definido en docs; queda **backlog Sprint 02** o **US-OPS**.

---

## 2. Identidad y principios (lectura obligatoria)

| Documento | Ruta | Uso |
|-----------|------|-----|
| Visión, principios no negociables, métricas A/B | [`00_IDENTIDAD_PROYECTO.md`](./00_IDENTIDAD_PROYECTO.md) | BT2 = protocolo conductual y riesgo; español en UI; traducción humana de métricas; API-first y CDM; sin scraping como base. |
| Zurich Calm: tokens, tipografía, componentes firma | [`04_IDENTIDAD_VISUAL_UI.md`](./04_IDENTIDAD_VISUAL_UI.md) | Bordes 1px, Inter + Geist Mono, semántica DP vs equity vs warning; liquidación y bóveda. |
| Contrato para redactar US | [`01_CONTRATO_US.md`](./01_CONTRATO_US.md) | Secciones 1–10; prefijos `US-BE`, `US-FE`, `US-DX`, `US-OPS`. |
| Rutas V1 / V2 en paralelo | [`03_RUTAS_PARALELAS_V1_V2.md`](./03_RUTAS_PARALELAS_V1_V2.md) | V2 bajo `/v2/*`; V1 sigue. |
| Playbook híbrido diseño + ejecución | [`02_PLAYBOOK_HIBRIDO.md`](./02_PLAYBOOK_HIBRIDO.md) | Flujo Gemini + Cursor. |
| Índice carpeta BetTracker2 | [`README.md`](./README.md) | Orden: US → TASKS → DECISIONES → QA. |

---

## 3. Sprint 01 — fuentes de verdad

| Recurso | Ruta |
|---------|------|
| Historias de usuario (incl. US-BE-001, US-DX-001) | [`sprints/sprint-01/US.md`](./sprints/sprint-01/US.md) |
| Tareas con checkboxes | [`sprints/sprint-01/TASKS.md`](./sprints/sprint-01/TASKS.md) |
| Decisiones de producto / UX | [`sprints/sprint-01/DECISIONES.md`](./sprints/sprint-01/DECISIONES.md) |
| QA por bloques | [`sprints/sprint-01/QA_CHECKLIST.md`](./sprints/sprint-01/QA_CHECKLIST.md) |
| Flujo maestro y journey | [`sprints/sprint-01/all_flow_sprint001.md`](./sprints/sprint-01/all_flow_sprint001.md) |
| Rol agente FE (BA/PM front) | [`agent_roles/front_end_agent.md`](./agent_roles/front_end_agent.md) |

**Refs HTML/mock:** `docs/bettracker2/sprints/sprint-01/refs/` (convención `us_fe_*`).

---

## 4. Arquitectura frontend V2 (`apps/web`)

### 4.1 Rutas principales (`/v2/*`)

Orden de **guards** acordado: **Auth → Contrato de disciplina → Diagnóstico → Búnker** (sin atajos por URL que salten pasos).

Vistas típicas: Santuario (`/v2/sanctuary`), Bóveda (`/v2/vault`), Liquidación (`/v2/settlement/:pickId`), Cierre del día (`/v2/daily-review`), Ledger (`/v2/ledger`), Rendimiento (`/v2/performance`), Perfil (`/v2/profile`), Ajustes (`/v2/settings`).

### 4.2 Estado cliente (Zustand + persistencia)

Persistencia local cifrada (XOR/envoltorio) — detalle en `DECISIONES.md` y `apps/web/src/lib/bt2EncryptedStorage.ts`.

| Store (nombre archivo) | Responsabilidad |
|------------------------|-----------------|
| `useUserStore.ts` | Sesión mock, contrato, DP, onboarding, perfil diagnóstico. |
| `useBankrollStore.ts` | Bankroll COP, stake %, unidad. |
| `useVaultStore.ts` | IDs desbloqueados; **`accessTier === 'open'`** implica desbloqueo lógico **sin** gastar DP. |
| `useTradeStore.ts` | Picks liquidados, **ledger** filas. |
| `useSessionStore.ts` | Día operativo (`operatingDayKey`), gracia, bloqueo de estación. |
| `useTourStore.ts` | Tours vistos por clave de ruta. |

**Regla clave bóveda:** los picks **open** deben ser navegables/liquidable sin slide; **premium** requieren desbloqueo con **50 DP** (`VAULT_UNLOCK_COST_DP`).

### 4.3 Datos mock actuales (hasta que el BE alimente)

- **Feed bóveda / liquidación:** `apps/web/src/data/vaultMockPicks.ts` — tipo **`VaultPickCdm`** (ver §5).
- **Mapa mercado ES:** `apps/web/src/lib/marketLabels.ts` — `marketClass` → etiqueta UI (nunca mostrar código crudo como única etiqueta).

---

## 5. Contratos de datos que el FE asume (CDM cliente)

### 5.1 `VaultPickCdm` (pick en bóveda / pre-liquidación)

Campos usados en UI (nombre TS en cliente):

- `id`, `marketClass`, `eventLabel`, `titulo`, `suggestedDecimalOdds`, `edgeBps`
- **`selectionSummaryEs`** — línea de apuesta en español (US-FE-024)
- `traduccionHumana`, `curvaEquidad`
- **`accessTier`:** `'open' | 'premium'`
- Coste de desbloqueo premium: constante **50 DP** (no por pick en el tipo actual)

### 5.2 Liquidación

- Modo verificación: **`trust`** (MVP) — constante en `apps/web/src/lib/bt2SettlementMode.ts`; copy visible en `SettlementPage`.
- Entrada operador: resultado **Ganancia / Pérdida / Empate**, reflexión ≥10 caracteres, **cuota en casa opcional**; PnL usa cuota casa si válida, si no cuota sugerida.
- Umbrales alineación sugerida vs casa: **±0.02** alineada, **±0.08** cercana (resto desviada) — lógica en `SettlementPage.tsx`.

### 5.3 `LedgerRow` (post-liquidación)

Persistido en `useTradeStore` (campos relevantes para BE):

- `pickId`, `marketClass`, `titulo`, `eventLabel`, **`selectionSummaryEs`**
- `outcome`, `reflection`, `pnlCop`, `stakeCop`, `decimalCuota`, **`suggestedDecimalOdds`**, **`bookDecimalOdds`**
- `settledAt`, `earnedDp`

El backend futuro debería poder **rehidratar** el ledger con el mismo shape (o versión versionada con migración).

### 5.4 Sesión / día operativo

Conceptos en `useSessionStore` y US-FE-012 / US-FE-014:

- `operatingDayKey` (YYYY-MM-DD en TZ usuario)
- Gracia 24 h, pendientes del día anterior, bloqueo de estación

---

## 6. Stub API ya existente (`apps/api`) — handoff técnico

Implementación **US-BE-001**: rutas bajo **`/bt2`** (sin BD; JSON estático alineado a demo bóveda).

| Método | Ruta | Contenido aproximado |
|--------|------|----------------------|
| GET | `/bt2/meta` | `contractVersion`, `settlementVerificationMode` (`trust`) |
| GET | `/bt2/session/day` | `operatingDayKey`, `userTimeZone`, flags stub |
| GET | `/bt2/vault/picks` | Lista picks CDM + `marketLabelEs`, `unlockCostDp`, etc. |
| GET | `/bt2/metrics/behavioral` | Placeholder métricas §B de `00` (demo) |

**OpenAPI:** `/docs` con servidor en marcha.

**Gap:** el **FE aún no consume** estas rutas por defecto; sustitución de `vaultMockPicks` es **Sprint 02 (US-FE)** + **US-BE** persistencia.

---

## 7. Qué debe hacer el backend (expectativas de producto)

1. **Sustituir mocks** con API interna estable: mismos conceptos que **US-DX-001** en [`sprints/sprint-01/US.md`](./sprints/sprint-01/US.md) (pick CDM ampliado, sesión diaria, modo liquidación).
2. **No** exponer nombres de proveedor ni DTOs crudos en contratos de UI (ACL/CDM servidor).
3. **Métricas B** de [`00_IDENTIDAD_PROYECTO.md`](./00_IDENTIDAD_PROYECTO.md): estructura técnica + posibilidad de **copy humano** derivado (ROI, drawdown, bloqueo conductual, hit rate).
4. **Modo `verified`:** liquidación asistida por resultado canónico — explícitamente **vNext**; ver `DECISIONES.md` (modo confianza vs verificado).
5. **Reloj / TZ:** en producción, fuente de verdad anti-manipulación de hora local (ya anotado en DECISIONES respecto a US-FE-012).

---

## 8. Backlog sugerido — Sprint 02 (no priorizado aquí)

- Plan de **rollback** / feature flags (US-OPS o sección en sprint 02).
- **Consumo FE** de `/bt2` o API definitiva; eliminación de duplicación mock vs servidor.
- **US-BE:** persistencia usuario, ledger servidor, auth real (si aplica).
- **T-039:** desbloqueo funcional recalibración cuando contadores reales existan.
- **Modo verified** + jobs de resultado canónico (US-BE + US-DX).
- **Tests E2E** o checklist PO manual firmado en CI si el equipo lo adopta.
- Revisar **orden de líneas en PickCard** vs checklist literal (mercado → selección → evento → tesis); funcionalmente cumple US-FE-024; alinear wording QA si se desea.

---

## 9. Referencias rápidas de código (mapa para el arquitecto)

| Tema | Ruta |
|------|------|
| Página liquidación | `apps/web/src/pages/SettlementPage.tsx` |
| Tarjeta bóveda | `apps/web/src/components/vault/PickCard.tsx` |
| Lista bóveda | `apps/web/src/pages/VaultPage.tsx` |
| Mock picks | `apps/web/src/data/vaultMockPicks.ts` |
| Ledger / liquidación | `apps/web/src/store/useTradeStore.ts` |
| Desbloqueo / open tier | `apps/web/src/store/useVaultStore.ts` |
| Schemas stub BT2 | `apps/api/bt2_schemas.py`, `apps/api/bt2_router.py` |

---

*Este archivo no sustituye a `US.md` ni a `DECISIONES.md`; sirve como **puerta de entrada** para quien entre al proyecto por la capa backend o producto API.*

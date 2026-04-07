# Sprint 01 - Decisiones tecnicas

Registra decisiones de arquitectura y trade-offs.

## Formato

- Decision:
- Contexto:
- Alternativas consideradas:
- Elegida:
- Impacto:
- Fecha:

---

## US-FE-001 — Gate V2 y persistencia (2026-04-03)

- **Decision:** Separar URL de tablero V2 (`/v2/dashboard`) de la sesión de entrada (`/v2/session`) y proteger el primero con el estado de Zustand (`isAuthenticated`, `hasAcceptedContract`).
- **Contexto:** La US exige impedir acceso al dashboard sin contrato y registrar intentos de bypass en consola.
- **Alternativas consideradas:** Mantener solo `/v2/session` renderizando `BunkerLayout` sin cambiar la URL; rechazada porque no permite deep links ni comprobar bypass por ruta.
- **Elegida:** `V2DashboardPage` redirige a `/v2/session` y emite `console.warn` si falta sesión o contrato; tras contrato, `Navigate` a `/v2/dashboard`.
- **Impacto:** Rutas documentadas en `03_RUTAS_PARALELAS_V1_V2.md`; comportamiento observable en DevTools.

- **Decision:** Persistencia del store V2 con ofuscación XOR por bytes y clave derivada de `window.location.origin` (envoltorio `{ v, d }` en localStorage), con lectura compatible del JSON plano legado de Zustand.
- **Contexto:** Criterio no funcional US-FE-001 “cifrado básico” en localStorage; sin servidor de claves.
- **Alternativas consideradas:** JSON plano; Web Crypto AES-GCM con clave fija en bundle (similar riesgo, más código).
- **Elegida:** `apps/web/src/lib/bt2EncryptedStorage.ts` (`createBt2EncryptedLocalStorage` como `StateStorage` de Zustand 5) compuesto con `createJSONStorage()` en `useUserStore`.
- **Impacto:** Primera escritura tras upgrade cifra el blob; usuarios con estado legado siguen pudiendo leer hasta el próximo `setItem`.

---

## US-FE-002 — Treasury y rutas V2 (fecha según commit)

- **Decision:** Estado de bankroll y stake en `useBankrollStore` persistido con el mismo `createBt2EncryptedLocalStorage` que el usuario V2; equity del header lee solo de ese store.
- **Contexto:** US pide cálculo de unit value, modal de capital y triggers automático/manual/settings.
- **Elegida:** `TreasuryModal` + auto-apertura si `confirmedBankrollCop === 0`; `V2SessionGate` compartido para `/v2/dashboard` y `/v2/settings`; observabilidad en confirm con `console.info` prefijo `[BT2]`.
- **Impacto:** Rutas documentadas en `03_RUTAS_PARALELAS_V1_V2.md`.

---

## Producto — Día calendario, cierre automático, gracia 24 h y consecuencias (2026-04-04)

- **Decisión:** El **día operativo** (topes de DP, “picks del día”, corte de sesión disciplinada) se ancla al **día calendario** en la **zona horaria del usuario** (perfil / dispositivo según implementación), no al ciclo manual arbitrario de apertura de estación.
- **Contexto:** Coherencia con copy (“hoy”), límites anti-farming y ritual de cierre; el usuario puede olvidar cerrar la estación.
- **Alternativas consideradas:** Definir “día” solo como tiempo entre “abrir” y “Cerrar estación”; rechazada para esta capa porque desalinea topes y feed diario con expectativa social de calendario.
- **Elegida:** Corte por **fin de día local**; la app debe poder **inspeccionar estado abierto** al cambiar de día (y al foreground / heartbeat razonable) y: (1) **cerrar automáticamente** lo que el sistema pueda resolver sin el usuario (p. ej. en vNext con resultado canónico CDM); (2) **dejar constancia** de liquidaciones / cierre de estación pendientes del día que cerró.
- **Gracia:** **Ventana de 24 horas** tras el fin del día calendario para que el operador **liquide picks pendientes** y/o **complete el cierre de estación** del día anterior (fuerza mayor, copy explícito en UI).
- **Consecuencias si tras la gracia sigue incompleto:** **Castigo / penalización conductual** auditable (tabla operativa a calibrar: p. ej. no abonar DP de cierre del día, reducción simbólica de DP, bloqueo temporal de desbloqueos premium, degradación de métrica de integridad). Debe quedar **regla escrita** en US, no solo mensaje genérico.
- **Impacto:** US-FE-012; revisión de US-FE-007; en producción, **US-BE** para fuente de verdad de reloj y TZ (anti-manipulación de hora local).

---

## Producto — Onboarding: cierre fase A y fase B economía DP (2026-04-04)

- **Decisión:** Tras completar el último hito funcional del onboarding (p. ej. **Treasury** confirmado con bankroll &gt; 0), mostrar **un solo bloque de copy** que **liste** identidad, contrato, diagnóstico y capital declarado; **una animación sobria** (Zurich Calm) que celebre el cierre de **fase A** y muestre el **abono único de DP** acordado (p. ej. +250 DP en una sola acreditación, no cuatro micro-abonos en UI).
- **Fase B (inmediata o en primer acceso a Bóveda):** tour corto (2–4 pasos) que explique **economía interna**: qué son los DP, **lecturas gratuitas vs premium** del día, cómo se **ganan** (liquidación, cierre, reconciliación) y cómo se **gastan** (desbloqueo), para evitar frustración (“solo veo dos picks”).
- **Impacto:** US-FE-011; posible ruta dedicada o modal secuencial; alineado a `00_IDENTIDAD_PROYECTO.md` y `04_IDENTIDAD_VISUAL_UI.md`.

---

## US-FE-022 — Cuota casa: obligatoria vs advertencia; umbrales de alineación (T-057, 2026-04)

- **Decisión:** La cuota decimal en la casa es **opcional** (MVP suave). Si el operador no la introduce, el sistema usa la cuota sugerida por el CDM y lo indica con microcopy. No bloquea el envío. Razón: el flujo ya exige reflexión y reconciliación; añadir otro campo obligatorio aumentaría la fricción sin valor claro en MVP.
- **Umbrales de alineación** (constantes en código, `SettlementPage.tsx`):
  - **Alineada:** diferencia absoluta ≤ 0.02 (±0.02)
  - **Cercana:** diferencia absoluta ≤ 0.08
  - **Desviada:** diferencia absoluta > 0.08
- **PnL:** Si la cuota casa está presente, se usa para el cálculo de PnL y se persiste en `LedgerRow.bookDecimalOdds`; de lo contrario se usa la cuota sugerida. La cuota activa se persiste como `decimalCuota` en el ledger.
- **Monto apostado en casa (COP):** No implementado en T-057 (fuera del tiempo de tarea). Copy en UI informa que el monto mostrado es la unidad de protocolo según Tesorería.

## US-FE-023 — Migración de picks persist (T-058, 2026-04)

- **Decisión:** Usuarios con `unlockedPickIds` históricos de picks que ya no existen en el nuevo dataset de 7 picks mantendrán IDs huérfanos en el store (inofensivos — `isUnlocked` devuelve false si el ID no coincide con un pick existente, o true si coincide y es open). No se borra la persistencia.
- **Reset recomendado en QA:** si un tester nota comportamiento raro con picks del dataset anterior (v2-p-008 … v2-p-020), usar el panel de Ajustes → Reinicio de datos locales.

## Semántica de color — T-053 (US-FE-020, 2026-04)

- **Capital en riesgo (SettlementPage):** cambiado de `#6d3bd7` (accent DP) a `#914d00` (warning) — el dinero en riesgo requiere tono de advertencia, no de disciplina.
- **PnL potencial (SettlementPage):** cambiado a `#059669` (equity emerald) — representa ganancia monetaria potencial, no DP.
- **Saldo vault / bankroll (SettlementPage):** cambiado de neutro `#26343d` a `#059669` — capital real siempre en equity green.
- **P/L neto positivo (DailyReviewPage):** cambiado de `#6d3bd7` a `#059669` — resultado monetario de sesión = dinero real.
- **ROI global (PerformancePage):** cambiado de `#6d3bd7` a `#059669` — retorno sobre capital real.
- **Regla confirmada:** `#6d3bd7` / `#8B5CF6` = solo DP y elementos de disciplina; `#059669` / `#10B981` = solo capital real y P&L monetario.

## Producto — Liquidación y DP: modo confianza (MVP) vs verificado (vNext) (2026-04-04)

- **Decisión:** **Congelar principio:** en **producción madura**, el abono de DP por liquidación podrá **condicionarse** a la **concordancia** entre el resultado declarado por el usuario y el **resultado canónico del evento** en el CDM (anti-simulación de gestiones solo para farmear DP).
- **MVP / mock local:** modo **confianza** con **topes diarios**, fricción (reflexión, cierre) y reglas de sesión; sin pretender verificación externa en cliente.
- **Implementación del modo verificado:** **Improvement posterior** — **US-DX** (payload de resultado de mercado, estado de verificación) + **US-BE** (jobs, fuentes, reglas push/void).
- **Impacto:** US-FE-006 nota de evolución; US-DX-001 stub ampliado; backlog BE explícito.

---

## US-FE-019 — Revisión PO frente a `04_IDENTIDAD_VISUAL_UI.md` (2026-04-04)

- **Decisión:** Cerrar el ítem de Definition of Done «Revisión PO contra 04» con **verificación de ingeniería** alineada al checklist de la US: copy ES (T-051), patrón métrica + línea humana en vistas piloto (T-052), sin nuevas violaciones de semántica de color tras T-053, y tours extendidos T-054–T-055 dentro de Zurich Calm.
- **Contexto:** El DoD pedía revisión explícita contra el documento visual `04`; los entregables técnicos del sprint ya implementan esos criterios.
- **Elegida:** Marcar DoD en `US.md` y dejar constancia aquí; cualquier matiz visual posterior se trata como refinement de producto, no como bloqueo del hito +90 % identidad FE.

---

## US-BE-001 — API BT2 stub (Sprint 01, 2026-04-04)

- **Decisión:** Exponer rutas bajo prefijo **`/bt2`** sin persistencia en esta iteración: **JSON estático en memoria** que refleja el contrato **US-DX-001** (sesión por día, picks CDM ampliados, modo `settlement_verification_mode: trust`, placeholders de métricas conductuales para copy humano).
- **Contexto:** El API existente (`/dashboard`, `/picks`, etc.) sirve al scrapper SQLite y no al modelo mental V2; el stub desacopla el handoff FE ↔ BE sin mezclar DTOs legacy.
- **Alternativas consideradas:** Ampliar tablas SQLite desde el día 1; rechazada por alcance Sprint 01 y por riesgo de mezclar pipelines.
- **Seguridad local:** Igual que `/health`, las rutas `/bt2/*` no exigen `X-Local-Api-Key` mientras `WEB_API_KEY` esté vacío; en despliegue con clave, evaluar dependencia explícita o gateway.
- **Impacto:** `apps/api/bt2_router.py` + `bt2_schemas.py`; tareas T-060–T-062 en `TASKS.md`.

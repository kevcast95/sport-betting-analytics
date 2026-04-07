# Sprint 01 - Tasks

## Sincronización con el repo (2026-04)

Las tareas **T-001 … T-055** están implementadas en `apps/web` (abril 2026), incluido el plan +90 % (US-FE-019 … 021). **T-056 … T-059** cerradas (**US-FE-022** … **US-FE-024**). **Backend BT2 stub:** **T-060 … T-062** (**US-BE-001**) en `apps/api`. QA: `all_flow_sprint001.md` §3 **Bloque 12**.

**Orden recomendado para el agente ejecutor:** ver [`all_flow_sprint001.md`](./all_flow_sprint001.md) §3 **Bloque 12**.

**Nota T-039:** la sección de recalibración está maquetada; el botón sigue deshabilitado hasta contadores 30 días + 50 liquidaciones (US-FE-010 batch) — se marca hecha la parte de UI prevista en el sprint.

---

## Backlog ejecutable

- [x] T-001 (US-FE-001) - Implementar AuthPage con toggle Login/Signup y estética Zurich Calm.
- [x] T-002 (US-FE-001) - Crear componente global de "Contract of Discipline" con validación de 3 axiomas.
- [x] T-003 (US-FE-001) - Setup de Zustand store `useUserStore` para persistencia de sesión y contrato.
- [x] T-004 (US-FE-001) - Maquetar Layout Base (BunkerLayout) con Sidebar y Header (DP/Equity).
- [x] T-005 (US-FE-002) - Crear useBankrollStore con lógica de cálculo de unidad.
- [x] T-006 (US-FE-002) - Implementar TreasuryModal con Slider y estética Zurich Calm.
- [x] T-007 (US-FE-002) - Implementar lógica de auto-disparo (useEffect) si el bankroll es nulo al inicio de sesión.
- [x] T-008 (US-FE-002) - Vincular el clic del label de "Total Equity" en el Header para abrir el TreasuryModal.
- [x] T-009 (US-FE-003) - Crear el useVaultStore con el estado de picks y lógica de desbloqueo por DP.
- [x] T-010 (US-FE-003) - Desarrollar el componente PickCard con estados Locked (Blur) y Unlocked.
- [x] T-011 (US-FE-003) - Implementar el gesto "Slide to Unlock" usando framer-motion.
- [x] T-013 (US-FE-004) - Reordenar sidebar V2: Santuario primero, La Bóveda segundo.
- [x] T-014 (US-FE-004) - Rutas anidadas `/v2/*`: índice y post-login → `/v2/sanctuary`; `/v2/dashboard` → compat.
- [x] T-015 (US-FE-004) - Sidebar 1px + `lg` 1024px + barra móvil; iconos Bt2; log `[BT2]` en navegación.
- [x] T-016 (US-FE-005) - DiagnosticPage en modo foco (sin sidebar/header estándar) según `refs/us_fe_005_diagnostic.md`.
- [x] T-017 (US-FE-005) - Motor cuestionario paso a paso, auto-avance ~800ms y barra de progreso superior.
- [x] T-018 (US-FE-005) - OperatorPreview: integridad del sistema y señal de perfil en tiempo real.
- [x] T-019 (US-FE-005) - Algoritmo de pesos y asignación de perfil (Guardián / Francotirador / Volátil) en `useUserStore`.
- [x] T-020 (US-FE-005) - DiagnosticGuard en rutas V2: contrato → diagnóstico → Santuario.
- [x] T-021 (US-FE-006) - SettlementPage: layout auditoría y datos del pick activo.
- [x] T-022 (US-FE-006) - AssetSpecification y SettlementZone (ganancia / pérdida / push).
- [x] T-023 (US-FE-006) - Cálculo PnL y actualización de `useBankrollStore` + DP en `useUserStore`.
- [x] T-024 (US-FE-006) - Validador reflexión (mín. 10 caracteres) y confirmación doble.
- [x] T-025 (US-FE-007) - DailyReviewPage: ROI del día y P/L neto de sesión.
- [x] T-026 (US-FE-007) - Reconciliación saldo real vs proyectado.
- [x] T-027 (US-FE-007) - Discipline Score del día y reflexión profesional.
- [x] T-028 (US-FE-007) - Station lock: bloquear operativa tras cierre diario.
- [x] T-029 (US-FE-008) - LedgerPage: tabla y Geist Mono.
- [x] T-030 (US-FE-008) - Widgets eficiencia de protocolo y factor total de disciplina.
- [x] T-031 (US-FE-008) - Filtros por protocolo y búsqueda por ID.
- [x] T-032 (US-FE-008) - Modal detalle de entrada (reflexiones históricas).
- [x] T-033 (US-FE-009) - PerformancePage y layout de métricas ejecutivas.
- [x] T-034 (US-FE-009) - Curva de equity con toggle escala logarítmica.
- [x] T-035 (US-FE-009) - Protection level y checklist protocolo Alpha.
- [x] T-036 (US-FE-009) - Sentimiento global (mock) y ROI / win rate desde ledger.
- [x] T-037 (US-FE-010) - ProfilePage: rango, nivel, XP.
- [x] T-038 (US-FE-010) - Medallas de consistencia (iconos, tooltips).
- [x] T-039 (US-FE-010) - Centro de recalibración (30 días + 50 liquidaciones). *(UI + copy; desbloqueo funcional pendiente de contadores — ver nota arriba.)*
- [x] T-040 (US-FE-010) - Badge de rango visible en header V2.

### Ola US-FE-011 … 014 (cerrada en código)

- [x] T-041 (US-FE-011) - Pantalla/modal cierre onboarding fase A: copy único, animación sobria, abono único de DP.
- [x] T-042 (US-FE-011) - Tour economía DP (fase B): picks abiertos vs premium, ganar/gastar DP, enlace a día calendario.
- [x] T-043 (US-FE-012) - `operatingDayKey` (TZ usuario), detección cambio de día y avisos de pendientes del día anterior.
- [x] T-044 (US-FE-012) - Ventana de gracia 24 h y aplicación de consecuencias/penalizaciones documentadas (persistencia + `[BT2]`).
- [x] T-045 (US-FE-013) - [Improvement vs US-FE-006] `settlementVerificationMode: trust` centralizado + copy español modo confianza en Settlement.
- [x] T-046 (US-FE-014) - [Cambio vs US-FE-007] Coherencia `stationLockedUntilIso` / bóveda con `operatingDayKey` y gracia (implementar junto o después de US-FE-012).

- [x] T-047 (US-FE-015) - [Refinement vs US-FE-011] Copy de logro +250 DP + `OnboardingConfettiBurst` (framer-motion, paleta marca, `prefers-reduced-motion`).

- [x] T-048 (US-FE-016) - Tours contextuales por vista (primera visita + ayuda); **2 vistas piloto**: Santuario + Bóveda.

- [x] T-049 (US-FE-017) - [Refinement vs US-FE-001] Quitar leyenda «TOKEN DE AUTENTICACIÓN» / `SS-VAULT-*` del modal `DisciplineContract`; pie del modal reorganizado (sin hueco).

- [x] T-050 (US-FE-018) - [Refinement vs US-FE-005] `DiagnosticPage`: integridad en % + microcopy; estado operador en español (sin códigos `CALIBRATING_V0` como única etiqueta); fila de puntos como **DP** (no XP) + aclaración de vista previa si aplica.

### Ola +90 % identidad (US-FE-019 … 021)

- [x] T-051 (US-FE-019) - Barrido **copy español** en rutas `/v2/*`: eliminar o traducir inglés residual (labels, `aria-label`, toasts, placeholders); registro breve en PR de archivos tocados.

- [x] T-052 (US-FE-019) - Patrón **métrica + línea humana** (`04` § autoridad numérica): implementar en **3 vistas piloto** acordadas con PO (por defecto sugerido: **Santuario**, **Rendimiento**, **Perfil**) — bajo cada KPI crítico, una frase en sans que diga qué implica para el operador.

- [x] T-053 (US-FE-020) - **Auditoría semántica de color** vs `04_IDENTIDAD_VISUAL_UI.md`: equity/dinero real vs DP/accent vs warning; corregir violaciones obvias (sin rediseño completo). Documentar 1–3 decisiones en `DECISIONES.md` si hay ambigüedad.

- [x] T-054 (US-FE-021) - [Extensión US-FE-016] Tours contextuales **lote A:** **Liquidación** (`SettlementPage`) + **Cierre del día** (`DailyReviewPage`); mismas reglas que piloto (primera visita + ayuda, `useTourStore`).

- [x] T-055 (US-FE-021) - [Extensión US-FE-016] Tours **lote B:** **Ledger**, **Rendimiento**, **Perfil**, **Ajustes** (`V2SettingsOutlet` o equivalente) — puede partirse en sub-PRs si el alcance es grande.

### Ola US-FE-022 (liquidación — emulación casa)

- [x] T-056 (US-FE-022) - CDM mock: evento (local/visitante o `eventLabel`), **cuota decimal sugerida** en dato; mapa **`marketClass` → español**; `SettlementPage`: jerarquía evento vs tesis modelo; labels **Cuota decimal sugerida**; sección **Lectura del modelo** (o **Sugerencia del sistema**); mercado visible solo en ES.

- [x] T-057 (US-FE-022) - Input **cuota decimal en la casa** + estado **Alineada / Cercana / Desviada**; PnL preview usando cuota casa cuando exista; copy y/o campo opcional **monto apostado (COP)** según US-FE-022 §2; persistencia mínima en `useTradeStore`/ledger si aplica; tests + nota `DECISIONES.md` si obligatoriedad vs advertencia.

- [x] T-058 (US-FE-023) - Bóveda demo: **~7 picks** (3–4 **abiertos** sin costo DP de lectura + 2–3 **premium** con desbloqueo 50 DP); `accessTier` en CDM; `PickCard` + `VaultPage` con **preview evento** (local/visitante o `eventLabel`) y **resumen mercado ES** (mapa compartido con US-FE-022); copy “Lectura del modelo” / “Sugerencia del sistema”; cabecera conteo coherente; tests + nota migración persist si aplica.

- [x] T-059 (US-FE-024) - Label explícito **«Mercado»** en `SettlementPage`; campo CDM **`selectionSummaryEs`** en todos los mocks + UI en liquidación y `PickCard` (respetando blur premium); tests verdes; QA Bloque 12.

### Ola US-BE-001 (API BT2 stub)

- [x] T-060 (US-BE-001) - Modelos Pydantic **`bt2_schemas.py`**: sesión diaria, pick CDM (US-DX-001), meta (`settlementVerificationMode`), métricas conductuales placeholder §`00`.
- [x] T-061 (US-BE-001) - Router FastAPI **`bt2_router.py`**: `GET /bt2/meta`, `GET /bt2/session/day`, `GET /bt2/vault/picks`, `GET /bt2/metrics/behavioral` con datos estáticos coherentes con demo bóveda.
- [x] T-062 (US-BE-001) - Registrar router en `apps/api/main.py`; serialización JSON con alias camelCase; verificación manual `uvicorn` + `/docs`.

## Reglas

- Cada task debe referenciar una US con prefijo (`US-BE-###`, `US-FE-###`, etc.).
- No iniciar task sin criterios de aceptacion claros.

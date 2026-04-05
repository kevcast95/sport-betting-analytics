# Sprint 01 - Tasks

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
- [ ] T-016 (US-FE-005) - DiagnosticPage en modo foco (sin sidebar/header estándar) según `refs/us_fe_005_diagnostic.md`.

- [ ] T-017 (US-FE-005) - Motor cuestionario paso a paso, auto-avance ~800ms y barra de progreso superior.

- [ ] T-018 (US-FE-005) - OperatorPreview: integridad del sistema y señal de perfil en tiempo real.

- [ ] T-019 (US-FE-005) - Algoritmo de pesos y asignación de perfil (Guardián / Francotirador / Volátil) en `useUserStore`.

- [ ] T-020 (US-FE-005) - DiagnosticGuard en rutas V2: contrato → diagnóstico → Santuario.

- [ ] T-021 (US-FE-006) - SettlementPage: layout auditoría y datos del pick activo.

- [ ] T-022 (US-FE-006) - AssetSpecification y SettlementZone (ganancia / pérdida / push).

- [ ] T-023 (US-FE-006) - Cálculo PnL y actualización de `useBankrollStore` + DP en `useUserStore`.

- [ ] T-024 (US-FE-006) - Validador reflexión (mín. 10 caracteres) y confirmación doble.

- [ ] T-025 (US-FE-007) - DailyReviewPage: ROI del día y P/L neto de sesión.

- [ ] T-026 (US-FE-007) - Reconciliación saldo real vs proyectado.

- [ ] T-027 (US-FE-007) - Discipline Score del día y reflexión profesional.

- [ ] T-028 (US-FE-007) - Station lock: bloquear operativa tras cierre diario.

- [ ] T-029 (US-FE-008) - LedgerPage: tabla y Geist Mono.

- [ ] T-030 (US-FE-008) - Widgets eficiencia de protocolo y factor total de disciplina.

- [ ] T-031 (US-FE-008) - Filtros por protocolo y búsqueda por ID.

- [ ] T-032 (US-FE-008) - Modal detalle de entrada (reflexiones históricas).

- [ ] T-033 (US-FE-009) - PerformancePage y layout de métricas ejecutivas.

- [ ] T-034 (US-FE-009) - Curva de equity con toggle escala logarítmica.

- [ ] T-035 (US-FE-009) - Protection level y checklist protocolo Alpha.

- [ ] T-036 (US-FE-009) - Sentimiento global (mock) y ROI / win rate desde ledger.

- [ ] T-037 (US-FE-010) - ProfilePage: rango, nivel, XP.

- [ ] T-038 (US-FE-010) - Medallas de consistencia (iconos, tooltips).

- [ ] T-039 (US-FE-010) - Centro de recalibración (30 días + 50 liquidaciones).

- [ ] T-040 (US-FE-010) - Badge de rango visible en header V2.

## Reglas


- Cada task debe referenciar una US con prefijo (`US-BE-###`, `US-FE-###`, etc.).
- No iniciar task sin criterios de aceptacion claros.

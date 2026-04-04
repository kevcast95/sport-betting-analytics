# Sprint 01 - US (Fuente de verdad)

> Este archivo define que se implementa en Sprint 01.
> Todo cambio tecnico debe mapear a una US aqui.

## Estado del sprint

- Fecha inicio:
- Fecha fin:
- Owner:
- Estado: Planned / In Progress / Done

## US incluidas

Prefijos obligatorios por capa: `US-BE-###`, `US-FE-###`, `US-DX-###`, `US-OPS-###` (ver `../../01_CONTRATO_US.md`).

## Backend

### US-BE-001 - [PENDIENTE]

## Frontend

### US-FE-001 - Autenticación y Protocolo de Acceso (Búnker Gate)
1) Objetivo de negocio
Establecer la puerta de entrada segura a BetTracker 2.0, garantizando que el usuario acepte el Contrato de Disciplina antes de visualizar cualquier métrica financiera o deportiva.

2) Alcance
Incluye:

Pantalla de Auth unificada (V2) con toggle entre Login/Signup.

Modal de "Contract of Discipline" con 3 checkboxes obligatorios para acceso al Dashboard.

Layout base (BunkerLayout) con Sidebar y Header funcional.

Excluye:

Persistencia en base de datos real (se usará Mock Auth en este sprint).

3) Contexto tecnico actual
Modulos afectados:

apps/web/src/pages/AuthPage.tsx

apps/web/src/layouts/BunkerLayout.tsx

apps/web/src/store/useUserStore.ts

Referencias visuales (HTML de apoyo):

- `docs/bettracker2/sprints/sprint-01/refs/us_fe_001_login.md`
- `docs/bettracker2/sprints/sprint-01/refs/us_fe_001_signup.md`
- `docs/bettracker2/sprints/sprint-01/refs/us_fe_001_discipline_contract.md`
- `docs/bettracker2/sprints/sprint-01/refs/us_fe_001_bunker_layout.md`

Dependencias externas:

framer-motion, zustand, iconos inline (`apps/web/src/components/icons/`, sin Material Symbols en runtime).

4) Contrato de entrada/salida
JSON
{
  "input": {
    "authMode": "LOGIN | SIGNUP",
    "credentials": { "email": "string", "password": "password" }
  },
  "output": {
    "authStatus": "SUCCESS | FAILED",
    "userState": {
      "isAuthenticated": true,
      "hasAcceptedContract": false,
      "operatorName": "string"
    }
  }
}
5) Reglas de dominio
Regla 1: El acceso al tablero V2 (`/v2/dashboard`) está prohibido si `hasAcceptedContract` es false.

Regla 2: El botón "Commit to the Protocol" requiere que los 3 checks de axiomas sean true.

Regla 3: V2 únicamente. No afecta rutas ni componentes de la V1.

6) Criterios de aceptacion
Given un usuario no logueado, When intenta entrar a la app, Then debe ver el formulario de Auth con estética Zurich Calm.

Given un login exitoso, When hasAcceptedContract es falso, Then debe aparecer el modal del contrato bloqueando el resto de la UI.

7) No-funcionales
Performance: Transiciones de Auth < 300ms.

Observabilidad: Log en consola de intentos de bypass del contrato.

Seguridad: Persistencia de flags de contrato en localStorage con cifrado básico.

Compatibilidad: Renderizado responsivo para Desktop (1440px) y Laptop (1024px).

8) Riesgos y mitigacion
Riesgo: El usuario puede intentar forzar la URL del dashboard.

Mitigacion: Middleware de ruta que verifica el estado de hasAcceptedContract en Zustand.

Criterio de Rollback: Revertir a commit inicial de BunkerLayout si el estado global se corrompe en el refresh.

9) Plan de pruebas
Unitarias: Verificar el toggle del estado de Auth entre Login y Signup.

Integracion: Validar que el cambio en useUserStore dispare la apertura/cierre del modal del contrato.

Manual UI: Confirmar el uso de Geist Mono en campos de contraseña y tokens.

10) Definition of Done
[ ] Codigo implementado

[ ] Tipado estricto

[ ] Tests verdes

[ ] Documentacion actualizada en docs/bettracker2/

[ ] Sin acoplamiento a proveedor en UI/IA

### US-FE-002 - Configuración del Tesoro (Treasury Setup)

#### 1) Objetivo de negocio

Establecer el capital base y la unidad de riesgo operativa, permitiendo que el sistema calcule montos reales en moneda local para cada sugerencia de la Bóveda.

#### 2) Alcance

- Incluye:
  - Modal **Capital Management Protocol** alineado a la ref HTML `sprints/sprint-01/refs/us_fe_002_bankroll.md` (paleta y jerarquía Zurich Calm; en React **no** cargar Material Symbols ni CDN de Tailwind de la ref: portar tokens y layout).
  - Slider para **Stake Unit** entre **0,25%** y **5,00%** (pasos coherentes con UX; valor por defecto documentado en implementación).
  - Visualización en tiempo real del **Unit Value** (`bankroll × stake_pct / 100`) con tipografía monoespaciada (Geist Mono, misma línea que US-FE-001).
  - Sincronización del saldo mostrado en cabecera del Búnker (`BunkerLayout`) cuando el usuario confirma en el modal.
- Excluye:
  - Historial de depósitos/retiros (solo saldo inicial / capital de trabajo en este sprint).

#### 3) Contexto técnico actual

- Módulos afectados:
  - `apps/web/src/store/useBankrollStore.ts` (nuevo; persistencia con el mismo patrón cifrado que `useUserStore` vía `createJSONStorage` + `createBt2EncryptedLocalStorage`).
  - `apps/web/src/components/TreasuryModal.tsx` (nuevo).
  - `apps/web/src/layouts/BunkerLayout.tsx` (lectura de bankroll / equity coherente con el store).
- Referencia visual:
  - `docs/bettracker2/sprints/sprint-01/refs/us_fe_002_bankroll.md`
- Dependencias externas:
  - zustand (persist), framer-motion (opcional, transiciones del modal), iconos en `apps/web/src/components/icons/` (sin `lucide-react` ni proveedor de iconos con nombre en UI).

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "initialBankroll": "number",
    "selectedStakePct": "number"
  },
  "output": {
    "unitValue": "number",
    "calculatedAt": "ISO8601"
  }
}
```

#### 5) Reglas de dominio

- Regla 1: `unitValue = initialBankroll * (selectedStakePct / 100)` (porcentaje expresado como número, p. ej. `2` para 2%).
- Regla 2: V2 únicamente. No alterar balance, bankroll ni APIs de la V1 (`/`, `/runs`, etc.).
- Regla 3: El botón de confirmación del modal permanece deshabilitado si el bankroll es `NaN` o `≤ 0`.
- Regla 4: Cada apertura del modal debe pedir **re-confirmación** del saldo (campo editable o paso explícito), según mitigación de riesgo abajo.
Regla 5: (Trigger Automático): Si el initialBankroll en el store es 0, el modal debe dispararse automáticamente al entrar al Dashboard por primera vez tras aceptar el contrato.

Regla 6: (Trigger Manual): El modal se dispara al hacer clic en el componente de "Equity/Bankroll" ubicado en el Header.

Regla 7: (Trigger de Configuración): Debe ser accesible desde la ruta `/v2/settings` y el ítem **Ajustes** del sidebar del Búnker.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given un usuario autenticado con contrato aceptado en el tablero V2 (`/v2/dashboard`), When abre el Treasury Modal, Then ve el bankroll actual resaltado con acento **esmeralda u oro** acorde a `04_IDENTIDAD_VISUAL_UI.md` y a la ref `us_fe_002_bankroll.md`.
2. Given el slider de stake, When el usuario lo fija en **2,00%** y el bankroll es **N**, Then el Unit Value mostrado es exactamente **N × 0,02**, formateado en moneda local (COP por defecto) con **Geist Mono**.

#### 7) No funcionales

- Performance: cálculo de Unit Value &lt; 10 ms en dispositivos objetivo.
- Observabilidad: `console` con prefijo `[BT2]` en cada cambio confirmado de `selectedStakePct` o bankroll (sin datos sensibles completos en claro si se evita loguear el monto entero; opcional truncar).
- Seguridad: persistencia del store de bankroll con **cifrado/ofuscación** en localStorage (mismo mecanismo que `useUserStore`).
- Compatibilidad: slider usable con teclado y tactil (rango acotado 0,25–5).

#### 8) Riesgos y mitigación

- Riesgo: desalineación entre saldo “real” y el introducido en el modal.
  - Mitigación: re-confirmación obligatoria al abrir el modal (copiar o revalidar monto).
- Criterio de rollback: restaurar últimos valores válidos en `useBankrollStore` ante entradas inválidas (`NaN`, &lt; 0) o corrupción del blob persistido.

#### 9) Plan de pruebas

- Unitarias: función pura `computeUnitValue(bankroll, stakePct)` con varios porcentajes y bordes (0,25; 5; bankroll 0).
- Integración: confirmar en modal actualiza estado leído por `BunkerLayout` (equity / bankroll visible).
- Manual UI: slider no sale del rango; confirmación bloqueada con bankroll inválido.

#### 10) Definition of Done

- [x] Código implementado
- [x] Tipado estricto
- [x] Tests verdes
- [x] Documentación actualizada en `docs/bettracker2/`
- [x] Sin acoplamiento a proveedor en UI/IA


### US-FE-003 - La Bóveda Central (The Vault)

#### 1) Objetivo de negocio

Implementar el centro de mando operativo donde el usuario visualiza, analiza y desbloquea oportunidades de inversión (+EV) utilizando su saldo de Puntos de Disciplina (DP).

#### 2) Alcance

- Incluye:
  - Rejilla de tarjetas de picks (V2) con estados **bloqueado** y **desbloqueado**, alineada a la ref `docs/bettracker2/sprints/sprint-01/refs/us_fe_003_vault.md` (tokens Zurich Calm; sin Material/CDN en runtime).
  - Gestión de desbloqueo tipo **deslizar para confirmar** que descuenta DP en `useUserStore`.
  - Tras desbloquear: mostrar la **traducción humana** (copy conductual) y curva de equity (mock CDM).
- Excluye:
  - Formulario de registro / evaluación de riesgo del pick (otra US).

#### 3) Contexto técnico actual

- Módulos afectados:
  - `apps/web/src/pages/VaultPage.tsx`
  - `apps/web/src/components/vault/PickCard.tsx`
  - `apps/web/src/store/useVaultStore.ts`
  - `apps/web/src/data/vaultMockPicks.ts` (mocks CDM, sin nombres de proveedor)
- Referencia visual:
  - `docs/bettracker2/sprints/sprint-01/refs/us_fe_003_vault.md`
- Dependencias externas:
  - framer-motion (blur, deslizamiento, transiciones).

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "disciplinePoints": "number",
    "pickId": "string"
  },
  "output": {
    "isUnlocked": "boolean",
    "remainingDP": "number",
    "unlockedContent": {
      "humanTranslation": "string",
      "equityCurveData": "array"
    }
  }
}
```

#### 5) Reglas de dominio

- Regla 1: Costo de desbloqueo por defecto **50 DP** (parametrizable en código).
- Regla 2: Si DP &lt; 50, el control de desbloqueo deshabilitado y mensaje **«Disciplina insuficiente»**.
- Regla 3: Solo V2. Feed con **modelo canónico (CDM)**; mocks sin datos crudos de API de proveedor.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given un pick bloqueado, When el usuario completa el gesto de deslizar para desbloquear, Then se descuenta el costo en DP y el contenido aparece con **fundido** (fade-in).
2. Given un pick ya desbloqueado, When el usuario recarga la página, Then el pick sigue desbloqueado (persistencia en Zustand).

#### 7) No funcionales

- Performance: grid de ~20 tarjetas sin degradar FPS perceptible.
- Observabilidad: log del id del pick desbloqueado (prefijo `[BT2]`).
- Seguridad: la traducción humana y datos sensibles del pick **no** deben estar en el DOM hasta desbloquear (sin texto oculto solo por CSS).
- Compatibilidad: gesto fluido en trackpad y táctil.

#### 8) Riesgos y mitigación

- Riesgo: desbloqueos accidentales.
  - Mitigación: deslizar en lugar de clic único.
- Rollback: si fallara la carga del contenido tras cobro, revertir DP y quitar id desbloqueado (en mocks no aplica; hook preparado).

#### 9) Plan de pruebas

- Unitarias: descuento exacto de DP y persistencia de ids desbloqueados.
- Integración: `PickCard` refleja estado según store.
- Manual UI: tipografía y espaciado acordes a `04_IDENTIDAD_VISUAL_UI.md` y la ref.

#### 10) Definition of Done

- [x] Código implementado conforme a `04_IDENTIDAD_VISUAL_UI.md` e identidad (copy en español).
- [x] Tipado estricto (TS).
- [x] Tests verdes.
- [x] Documentación actualizada en `docs/bettracker2/`.
- [x] Sin acoplamiento a proveedor (mocks CDM).

### US-FE-004 - Navegación estructural (jerarquía del sidebar)

#### 1) Objetivo de negocio

Reordenar el sidebar V2 para que **Santuario** sea el primer ítem y la **entrada por defecto** tras sesión, con transición clara hacia **La Bóveda**.

#### 2) Alcance

- Incluye:
  - Primer ítem de navegación: **Santuario** (`/v2/sanctuary`); segundo: **La Bóveda** (`/v2/vault`).
  - Vista de contenido **Santuario** (solo cuerpo de página; ref compuesta en Stitch: no copiar chrome extra del HTML).
  - Estados activo/hover Zurich Calm en ítems con `NavLink`.
  - Compatibilidad **tablet**: sidebar ancho fijo solo desde **1024px** (`lg:`); por debajo, barra de navegación compacta.
- Excluye:
  - RBAC del menú.
  - Cambiar la ruta raíz **V1** `/` (sigue siendo dashboard clásico).

#### 3) Contexto técnico actual

- Módulos afectados:
  - `apps/web/src/layouts/BunkerLayout.tsx` (sidebar + outlet + títulos por ruta)
  - `apps/web/src/layouts/V2ProtectedLayout.tsx`
  - `apps/web/src/App.tsx` (rutas anidadas bajo `/v2`)
  - `apps/web/src/pages/SanctuaryPage.tsx`, `apps/web/src/pages/VaultPage.tsx`, `apps/web/src/pages/V2SettingsOutlet.tsx`
  - `apps/web/src/components/icons/bt2Icons.tsx` (`Bt2HomeIcon` para Santuario)
- Referencia visual (tokens/layout; sin CDN en runtime): `docs/bettracker2/sprints/sprint-01/refs/us_fe_004_sanctuaryt.md`
- Iconos: **Bt2** (alineado al resto de V2); no añadir `lucide-react` solo por esta US.

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "currentPath": "string",
    "menuConfig": [
      { "label": "Santuario", "order": 1 },
      { "label": "La Bóveda", "order": 2 }
    ]
  },
  "output": {
    "activeRoute": "string"
  }
}
```

#### 5) Reglas de dominio

- Regla 1: **Santuario** es el primer ítem del menú lateral (y de la barra móvil).
- Regla 2: Tras login + contrato, destino por defecto **`/v2/sanctuary`**; **`/v2`** redirige al índice Santuario; **`/v2/dashboard`** redirige a **`/v2/sanctuary`** (compat).
- Regla 3: Solo V2; labels en español en UI.
- Regla 4: La ref Stitch es global: implementar **solo** la vista Santuario + orden de nav; no añadir elementos de sidebar/header no pedidos.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given usuario autenticado con contrato, When se renderiza el sidebar, Then el primer ítem enlazado es **Santuario**.
2. Given ruta **La Bóveda**, When se renderiza el sidebar, Then **Santuario** en reposo y **La Bóveda** activa.

#### 7) No funcionales

- Performance: navegación por React Router (sin recarga completa).
- Observabilidad: `console.info` con prefijo `[BT2]` al cambiar de módulo principal (Santuario, La Bóveda, Ajustes).
- Seguridad: sin contrato aceptado, `V2SessionGate` impide el layout V2 (equivalente a no mostrar el shell autenticado).
- Compatibilidad: sidebar colapsado bajo 1024px con alternativa táctil en barra superior.

#### 8) Riesgos y mitigación

- Riesgo: solapamiento con menú V1 → V2 bajo `/v2/*` y copy distintivo.
- Rollback: restaurar orden de rutas anterior si hay bucles de redirección.

#### 9) Plan de pruebas

- Unitarias / integración: rutas protegidas, Santuario vs Bóveda, regresión de sesión.
- Manual UI: borde lateral 1px y tipografía acordes a `04_IDENTIDAD_VISUAL_UI.md`.

#### 10) Definition of Done

- [x] Código implementado
- [x] Tipado estricto
- [x] Tests verdes
- [x] Documentación actualizada en `docs/bettracker2/`
- [x] Sin acoplamiento a proveedor en UI

### US-FE-005 - Diagnóstico de identidad operativa (The Mirror)

#### 1) Objetivo de negocio

Establecer un perfil conductual previo al uso operativo de BetTracker 2.0, calibrar el «cortafuegos conductual» y asignar un nivel de protección inicial antes de exponer datos de mercado.

#### 2) Alcance

- Incluye:
  - Flujo de **5** preguntas situacionales, navegación lineal (paso a paso).
  - **OperatorPreview**: integridad del sistema y señales de perfil en tiempo real tras cada respuesta.
  - Persistencia en `useUserStore` y **guard de ruta** obligatorio post-contrato.
  - Vista **focus** (sin sidebar/header estándar del búnker) según tokens en `docs/bettracker2/sprints/sprint-01/refs/us_fe_005_diagnostic.md` (sin CDN en runtime).
- Excluye:
  - Re-tomar el test libremente (bloqueado hasta 30 días y 50 liquidaciones en ledger; ver US-FE-010).

#### 3) Contexto técnico actual

- Módulos:
  - `apps/web/src/pages/DiagnosticPage.tsx`
  - `apps/web/src/store/useUserStore.ts` (p. ej. `operatorProfile`, `systemIntegrity`, `hasCompletedDiagnostic`)
  - Guard en rutas V2 (`DiagnosticGuard` / extensión de `V2SessionGate` o capa equivalente)
- Referencia visual: `docs/bettracker2/sprints/sprint-01/refs/us_fe_005_diagnostic.md`

#### 4) Contrato de entrada/salida

```json
{
  "input": { "hasAcceptedContract": true },
  "output": {
    "assignedProfile": "THE_GUARDIAN | THE_SNIPER | THE_VOLATILE",
    "systemIntegrity": "number (0.000 - 1.000)",
    "disciplinePointsPreview": "number"
  }
}
```

*(Los valores de perfil son claves técnicas; en UI siempre etiquetas en español: Guardián, Francotirador, Volátil — `00_IDENTIDAD_PROYECTO.md`.)*

#### 5) Reglas de dominio y cuestionario

- **Interacción:** al elegir una tarjeta, borde accent 1px (`#8B5CF6`, `04_IDENTIDAD_VISUAL_UI.md`); tras **800 ms** avance automático con transición (p. ej. slide); barra de progreso superior.
- **Integridad:** cada respuesta ajusta `systemIntegrity` con deltas acordados (p. ej. A +0.04, B 0, C −0.06 por dimensión; definir tabla en código y test unitario).
- **Fin de flujo:** al completar la pregunta 5, `hasCompletedDiagnostic: true` y redirección a `/v2/sanctuary`.

| # | Dimensión | Pregunta (resumen) | A (estratega) | B (impulsivo) | C (alto riesgo) |
|---|-----------|-------------------|---------------|----------------|-----------------|
| 1 | Nominalidad | Ganancia sugerida 5.000 COP por riesgo | Respeto el monto | Subo la apuesta | Busco pick más arriesgado |
| 2 | Tilt | Perdiste al 90′; ¿qué haces 5 min después? | Cierro la app / acepto varianza | Busco vivo para recuperar | Doblo la siguiente |
| 3 | Intuición | Favorito sin datos | No opero | Meto fuerte por instinto | Meto «por emoción» |
| 4 | Drawdown | Capital −5% semana | Recalibrar stake | Mantengo igual | Aumento riesgo |
| 5 | Honestidad | Aposté de más | Registro y asumo | Ignoro si gané | Compensar oculto |

#### 6) Criterios de aceptación (Given / When / Then)

1. Given `hasAcceptedContract` y **no** `hasCompletedDiagnostic`, When el usuario entra a cualquier ruta V2 protegida (p. ej. `/v2/sanctuary`, `/v2/vault`), Then se redirige a **`/v2/diagnostic`**.
2. Given una respuesta, When el usuario selecciona opción, Then `systemIntegrity` y el preview de perfil se actualizan al instante (números en **Geist Mono**).

#### 7) No funcionales

- Tipografía: datos numéricos e IDs en Geist Mono (`04_IDENTIDAD_VISUAL_UI.md`).
- UX: «Salir del foco» con confirmación y aviso de pérdida de progreso no guardado.
- Copy: **español** en toda la UI visible.

#### 8) Riesgos y mitigación

- Sesgo de complacencia → opciones neutras; integridad visible premia honestidad técnica.

#### 9) Plan de pruebas

- Integración: al terminar paso 5, `hasCompletedDiagnostic` y acceso a Santuario.
- Unitarias: función de scoring / deltas por respuesta.

#### 10) Definition of Done

- [ ] Maquetación y flujo alineados a `us_fe_005_diagnostic.md` (tokens Zurich Calm, sin Material/CDN).
- [ ] Cálculo de integridad y perfil en Zustand con tests.
- [ ] Guard de diagnóstico validado en el enrutador V2.

### US-FE-006 - Terminal de Auditoría (Settlement Terminal)
1) Objetivo de negocio
Proporcionar una interfaz técnica de liquidación para registrar el resultado de operaciones individuales, forzando una reflexión emocional que neutralice el impacto de la varianza y premie la disciplina procedural.

2) Alcance
Incluye:

Panel de Asset Specification con datos de lectura del pick (Cuota, Riesgo, PNL Potencial).

Settlement Zone: Botones de acción para Profit, Loss y Push/Void.

Widget de Recompensa por Disciplina: Visualización del DP REWARD: +25.

Campo de Post-Match Emotional Status: Input de texto obligatorio para la validación del cierre.

Excluye:

Edición de parámetros de entrada (Stake/Cuota) una vez en esta vista.

3) Contexto técnico actual
Módulos afectados:

apps/web/src/pages/SettlementPage.tsx

apps/web/src/store/useTradeStore.ts (Estado del pick: active -> settled).

apps/web/src/store/useBankrollStore.ts (Actualización de saldo real).

Referencia visual: `docs/bettracker2/sprints/sprint-01/refs/us_fe_006_settlement.md` (sin CDN en runtime).

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "pickId": "string",
    "outcome": "PROFIT | LOSS | PUSH",
    "reflection": "string (min 10 chars)"
  },
  "output": {
    "newBankroll": "number",
    "earnedDP": 25,
    "status": "ARCHIVED_IN_LEDGER"
  }
}
```

#### 5) Reglas de dominio
Regla 1 (Fricción Obligatoria): El botón "Confirmar Auditoría" permanece deshabilitado hasta que el campo de reflexión emocional sea completado.

Regla 2 (Incentivo al Reporte): Se otorgan +25 DP al finalizar el proceso, independientemente de si el resultado financiero fue Profit o Loss.

Regla 3 (Cálculo de PNL): - Profit: Capital Arriesgado * (Cuota - 1).

Loss: - Capital Arriesgado.

Push: 0 (Retorno de capital).

Regla 4 (Mensajes de Refuerzo): Al confirmar, el sistema debe mostrar un toast con copy conductual (ej. "Protocolo cumplido. La disciplina es el verdadero profit.").

6) Criterios de aceptación (Given / When / Then)
Given un pick activo en la Bóveda, When el usuario accede a la Terminal, Then debe visualizar sus datos técnicos en Geist Mono.

Given la selección de un resultado, When el usuario escribe su reflexión y confirma, Then el saldo global del Header debe actualizarse en tiempo real y el pick debe moverse al Ledger.

7) No funcionales
Visual: Estética Zurich Calm con bordes de 1px y colores de baja saturación.

UX: El input de reflexión debe tener un placeholder que incite a la honestidad (ej. "¿Mantuviste el plan a pesar de la varianza?").

Seguridad: Bloqueo de re-entrada a la URL de liquidación si el pick ya figura como settled.

8) Riesgos y mitigación
Riesgo: Error humano al elegir Profit en lugar de Loss.

Mitigación: Modal de confirmación final que resuma el impacto en el Bankroll antes de persistir.

9) Plan de pruebas
Unitarias: Validar las funciones de cálculo de PNL para cuotas decimales.

Integración: Asegurar que el useUserStore sume correctamente los DP tras la liquidación.

10) Definition of Done
[ ] Interfaz implementada según `docs/bettracker2/sprints/sprint-01/refs/us_fe_006_settlement.md` (tokens; sin CDN).

[ ] Lógica de liquidación vinculada al useBankrollStore.

[ ] Validación de campo de reflexión funcional.

### US-FE-007 - After-Action Review (Cierre del Día)
1) Objetivo de negocio
Proporcionar un ritual de cierre que reconcilie el saldo financiero proyectado con el real y genere una métrica de desempeño disciplinario global para la sesión, bloqueando el ledger para evitar operaciones impulsivas post-cierre.

2) Alcance
Incluye:

Resumen de sesión: Today's ROI y Net Profit/Loss.

Widget de Reconciliation: Campo de entrada para el saldo real de la casa de apuestas y comparativa contra el Projected Balance.

Discipline Score of the Day: Un indicador visual (0-100) basado en la adherencia al protocolo.

Professional Reflection: Área de texto para observaciones finales de la sesión.

Botón de acción "Close Station & Finalize Day".

Excluye:

Edición de auditorías individuales (deben estar cerradas en la US-FE-006).

3) Contexto técnico actual
Módulos afectados:

apps/web/src/pages/DailyReviewPage.tsx

apps/web/src/store/useSessionStore.ts (Nuevo; gestiona el estado de "Estación Abierta/Cerrada").

apps/web/src/store/useBankrollStore.ts (Ajuste por comisión o discrepancia).

Referencia visual: `docs/bettracker2/sprints/sprint-01/refs/us_fe_007_after_action.md` (sin CDN en runtime).

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "currentBankrollInExchange": "number",
    "dailyReflection": "string"
  },
  "output": {
    "isStationLocked": true,
    "finalDisciplineScore": "number",
    "reconciliationStatus": "PERFECT_MATCH | DISCREPANCY"
  }
}
```

#### 5) Reglas de dominio

Regla 1 (Bloqueo de Seguridad): Una vez ejecutado el "Close Station", el acceso a la Bóveda para nuevos picks queda deshabilitado hasta el siguiente ciclo de 24 horas o reset manual del administrador.

Regla 2 (Reconciliación): Si existe una discrepancia mayor al 1% entre el saldo real y el proyectado, el sistema resalta el valor en color error (rojo/púrpura oscuro) y pide una nota aclaratoria (ej. comisiones o depósitos externos).

Regla 3 (Score de Disciplina): El puntaje de 94/100 (ejemplo de imagen) se calcula promediando los DP ganados vs los picks operados y la velocidad de reporte.

6) Criterios de aceptación (Given / When / Then)
Given que el usuario ha liquidado todos sus picks del día, When accede al After-Action Review, Then debe ver el ROI acumulado de la sesión.

Given un saldo ingresado que coincide con el proyectado, When el usuario valida, Then el estatus debe cambiar a "Perfect Match" con tipografía Geist Mono.

7) No funcionales
Visual: Uso de gradientes suaves y desenfoques (backdrop-blur) según la estética Zurich Calm.

UX: El botón de cierre debe ser prominente (Púrpura marca) para indicar la importancia del rito.

8) Riesgos y mitigación
Riesgo: El usuario olvida cerrar la estación.

Mitigación: Notificación visual en el Santuario si hay picks liquidados pero la sesión sigue abierta al final del día.

9) Plan de pruebas
Integración: Confirmar que al cerrar la estación, el estado isLocked impida mutaciones en el useTradeStore.

10) Definition of Done
[ ] Interfaz implementada según `docs/bettracker2/sprints/sprint-01/refs/us_fe_007_after_action.md` (tokens; sin CDN).

[ ] Lógica de reconciliación de saldo operativa.

[ ] Bloqueo de UI post-cierre validado.


### US-FE-008 - El Libro Mayor Estratégico (The Strategic Ledger)
1) Objetivo de negocio
Proporcionar un registro cronológico, inmutable y auditable de todas las ejecuciones disciplinadas, permitiendo al usuario filtrar por protocolo y visualizar el impacto de su adherencia en los Puntos de Disciplina.

2) Alcance
Incluye:

Tabla de registros con columnas: Date, Strategic Protocol, Outcome, Discipline Points, y Action.

Sistema de filtrado por Protocolo (Alpha-9, Sigma-1, etc.) y búsqueda por ID de entrada.

Widget de Protocol Efficiency: Visualización porcentual del éxito del protocolo seleccionado.

Widget de Total Discipline Factor: Métrica agregada y barra de progreso de rango (Elite, Master, etc.).

Paginación y navegación entre registros pasados.

Excluye:

Edición de registros (el Ledger es de solo lectura por integridad histórica).

3) Contexto técnico actual
Módulos afectados:

apps/web/src/pages/LedgerPage.tsx

apps/web/src/components/ledger/LedgerTable.tsx

apps/web/src/store/useTradeStore.ts (Lectura del array settledPicks).

Referencia visual: `docs/bettracker2/sprints/sprint-01/refs/us_fe_008_strategic_ledger.md` (sin CDN en runtime).

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "filters": { "protocol": "string", "dateRange": "ISO8601" },
    "page": "number"
  },
  "output": {
    "entries": "Array<LedgerEntry>",
    "stats": { "efficiency": "number", "totalDP": "number" }
  }
}
```

#### 5) Reglas de dominio

Regla 1 (Integridad): Los datos mostrados en la columna Outcome deben incluir tanto el ROI porcentual como la etiqueta de estado (RECAP, PUSH, ROI) en los colores de la marca.

Regla 2 (Nomenclatura): El uso de Geist Mono es obligatorio para todas las fechas, IDs de protocolo y valores numéricos de DP.

Regla 3 (Acción Detallada): El botón "View Details" debe abrir un modal de solo lectura con la reflexión emocional capturada en la US-FE-006.

6) Criterios de aceptación (Given / When / Then)
Given un conjunto de picks liquidados, When el usuario accede al Ledger, Then debe ver la lista ordenada de forma descendentemente por fecha.

Given el filtro de protocolo, When el usuario selecciona "Alpha-9", Then la tabla y el widget de Protocol Efficiency deben actualizarse instantáneamente.

7) No funcionales
Performance: Renderizado de tabla mediante virtualización si supera los 100 registros para mantener 60 FPS.

Visual: Bordes de 1px, espaciado amplio y estética de "Reporte Ejecutivo".

8) Riesgos y mitigación
Riesgo: Sobrecarga de información visual.

Mitigación: Uso de estados vacíos (Empty States) elegantes si no hay registros para un filtro específico.

9) Plan de pruebas
Integración: Validar que los datos mostrados en el Ledger sean un reflejo exacto del estado settled del useTradeStore.

10) Definition of Done
[ ] Interfaz implementada según `docs/bettracker2/sprints/sprint-01/refs/us_fe_008_strategic_ledger.md` (tokens; sin CDN).

[ ] Filtros y búsqueda funcionales.

[ ] Tipado estricto en la interfaz LedgerEntry.

### US-FE-009 - Estrategia y Rendimiento (Strategy & Performance)
1) Objetivo de negocio
Visualizar el rendimiento macro del búnker mediante métricas de ROI, Drawdown y consistencia, permitiendo al usuario validar la eficacia de sus protocolos y su nivel de protección actual.

2) Alcance
Incluye:

Métricas Ejecutivas: Cuatro widgets principales: Overall ROI, Win Rate, Max Drawdown y Discipline Gained.

Equity Curve Performance: Gráfico de línea con toggle para escala logarítmica y filtros temporales (12 meses por defecto).

The Alpha Protocol Checklist: Estado de cumplimiento de los sub-protocolos (Liquidity, Variance, Psychological Readiness).

Protection Level Widget: Card destacada que muestra el estado de seguridad (ej. MAXIMUM) y el impacto del Discipline Score actual.

Global Sentiment: Widget visual con el estatus del mercado (Risk-Off/Risk-On).

Excluye:

Registro de nuevos datos (es una vista de lectura analítica).

3) Contexto técnico actual
Módulos afectados:

apps/web/src/pages/PerformancePage.tsx

apps/web/src/components/analytics/EquityChart.tsx

apps/web/src/store/useAnalyticsStore.ts (Nuevo; procesa datos históricos para gráficos).

Referencia visual: `docs/bettracker2/sprints/sprint-01/refs/us_fe_009_strategy_performance.md`.

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "timeRange": "1M | 6M | 1Y | ALL",
    "isLogScale": "boolean"
  },
  "output": {
    "equityData": "Array<{date: string, value: number}>",
    "metrics": { "roi": 18.4, "drawdown": -4.2, "winRate": 64.2 }
  }
}
```

#### 5) Reglas de dominio

Regla 1 (Integridad Visual): El gráfico de equidad debe usar el color Púrpura/Lavanda de la marca con un degradado de área suave hacia el fondo.

Regla 2 (Semántica de Color): El Max Drawdown se resalta en Oro/Naranja (alerta) en lugar de rojo agresivo, manteniendo la estética Zurich Calm.

Regla 3 (Checklist Dinámico): El ítem "Psychological Readiness Audit" debe aparecer como PENDING si el usuario no ha completado el After-Action Review (US-FE-007) de las últimas 24 horas.

6) Criterios de aceptación (Given / When / Then)
Given datos históricos en el Ledger, When el usuario entra a Performance, Then debe ver su ROI calculado dinámicamente con precisión de un decimal.

Given el widget de Protección, When el Discipline Score es > 1000, Then el estatus debe mostrar MAXIMUM con el badge de validación de integridad.

7) No funcionales
Performance: El gráfico debe renderizar fluidamente (usando Recharts o librería similar) con soporte para tooltips técnicos en Geist Mono.

UX: Los widgets de métricas deben tener un ligero "hover" que explique brevemente el cálculo al usuario.

8) Riesgos y mitigación
Riesgo: Gráficos vacíos para usuarios nuevos.

Mitigación: Mostrar "Empty State" con una curva proyectada o tutorial de cómo empezar a generar datos.

9) Plan de pruebas
Unitarias: Verificar la lógica de cálculo del ROI y Drawdown basada en el historial de transacciones.

10) Definition of Done
[ ] Interfaz implementada según `docs/bettracker2/sprints/sprint-01/refs/us_fe_009_strategy_performance.md` (tokens; sin CDN).

[ ] Gráfico de equidad interactivo y filtrable.

[ ] Widgets de métricas vinculados al estado global de analíticas.

### US-FE-010 - El Camino a la Maestría (Elite Progression Path)
1) Objetivo de negocio
Fomentar la retención y la adherencia al protocolo mediante un sistema de rangos y niveles basado en la acumulación de Discipline Points (DP), proporcionando un centro para la evolución de la identidad operativa del usuario.

2) Alcance
Incluye:

Perfil de Operador: Avatar (Arquitecto Alpha), Nivel actual y Barra de Progreso de XP.

Sistema de Rangos: Visualización de la jerarquía (ej. Novice -> Sentinel -> Elite -> Master).

Medallas de Consistencia: Grid de logros desbloqueables (ej. "7 días de reporte perfecto", "Drawdown controlado < 5%").

Centro de Recalibración: Acceso restringido para repetir el Diagnóstico de Identidad (US-FE-005).

Excluye:

Funciones sociales o comparativas con otros usuarios (el búnker es privado).

3) Contexto técnico actual
Módulos afectados:

apps/web/src/pages/ProfilePage.tsx

apps/web/src/components/profile/RankBadge.tsx

apps/web/src/store/useUserStore.ts (Lógica de niveles y desbloqueo de diagnóstico)

Referencia visual: `docs/bettracker2/sprints/sprint-01/refs/us_fe_010_progress_path.md` (cabecera / progresión); coherencia de widgets con `us_fe_005_diagnostic.md` donde aplique.

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "totalDP": "number",
    "daysActive": "number",
    "lastDiagnosticDate": "ISO8601"
  },
  "output": {
    "currentRank": "string",
    "isDiagnosticUnlockable": "boolean",
    "nextRankThreshold": "number"
  }
}
```

#### 5) Reglas de dominio

Regla 1 (Niveles): Cada nivel requiere un incremento exponencial de DP (ej. Nivel 1: 500 DP, Nivel 2: 1250 DP).

Regla 2 (Recalibración): El botón de "Tomar nuevo diagnóstico" solo se habilita si se cumplen ambas condiciones: 30 días desde el último test Y 50 picks liquidados en el Ledger.

Regla 3 (Visualización de Rango): El rango debe mostrarse con el badge de TIER II (o superior) en color Púrpura/Lavanda e icono de escudo.

6) Criterios de aceptación (Given / When / Then)
Given que un usuario alcanza los 1250 DP, When accede a su perfil, Then debe ver su estatus actualizado a LEVEL: ELITE.

Given la sección de recalibración, When el usuario NO cumple los requisitos de tiempo o picks, Then el botón debe estar deshabilitado con un tooltip que indique lo que falta.

7) No funcionales
Visual: Estética de "Gamer Pro" pero sobria (Zurich Calm), evitando colores infantiles o saturados.

UX: Uso de micro-interacciones (framer-motion) al pasar el cursor sobre las medallas para ver los requisitos de obtención.

8) Riesgos y mitigación
Riesgo: Desmotivación si los niveles son inalcanzables.

Mitigación: Niveles iniciales rápidos (Quick Wins) para reforzar el hábito de reporte.

9) Plan de pruebas
Unitarias: Validar la función calculateRank(points) con diferentes escenarios de DP acumulados.

10) Definition of Done
[ ] Interfaz de perfil implementada con barra de progreso funcional.

[ ] Lógica de desbloqueo de diagnóstico validada.

[ ] Grid de medallas maquetado con estados bloqueado/desbloqueado.

## Contratos

### US-DX-001 - [PENDIENTE]

## Operacion

### US-OPS-001 - [PENDIENTE]

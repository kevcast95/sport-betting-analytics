# Sprint 01 - US (Fuente de verdad)

> Este archivo define que se implementa en Sprint 01.
> Todo cambio tecnico debe mapear a una US aqui.

## Estado del sprint

- Fecha inicio: (sprint 01 — ver `TASKS.md` / historial repo)
- Fecha fin FE: **2026-04-04**
- Owner: (equipo)
- Estado: **Done (Frontend Sprint 01)** — US-FE-001 … US-FE-024 + QA; **US-BE-001** stub en `apps/api`. Pendientes operativos / integración → **Sprint 02** (ver `all_flow_sprint001.md` §6, `HANDOFF_BA_PM_BACKEND.md`).

## US incluidas

Prefijos obligatorios por capa: `US-BE-###`, `US-FE-###`, `US-DX-###`, `US-OPS-###` (ver `../../01_CONTRATO_US.md`).

## Backend

### US-BE-001 — API interna BT2 (stub CDM + sesión diaria, Sprint 01)

#### 1) Objetivo de negocio

Publicar una **API de lectura estable** (sin persistencia en BD en esta iteración) que materialice el contrato descrito en **US-DX-001**, para que el frontend V2 pueda **sustituir mocks locales** en sprints posteriores sin rediseñar tipos.

#### 2) Alcance

- Incluye:
  - Prefijo de ruta **`/bt2`** en `apps/api` (FastAPI), **independiente** del API del scrapper (`/dashboard`, `/picks`, etc.).
  - Esquemas Pydantic/OpenAPI para: estado de **día operativo** (`operating_day_key`, `user_time_zone`, `grace_until_iso` opcional), **picks CDM** ampliados (incl. `access_tier`, `unlock_cost_dp`, `suggested_decimal_odds`, `market_class`, `market_label_es`, `selection_summary_es`, narrativa / curva stub), **`settlement_verification_mode`** (`trust` en MVP), y **bloque placeholder** de métricas conductuales alineadas a `00_IDENTIDAD_PROYECTO.md` §B (valores demo + campos técnicos para copy UI).
  - Endpoints GET de **solo lectura** que devuelven JSON con **alias camelCase** donde aplica, alineado al consumo TypeScript del cliente.
- Excluye:
  - Autenticación de usuario final, base de datos BT2, jobs de proveedores, ACL real, modo `verified` de liquidación.

#### 3) Contexto técnico actual

- Implementación: `apps/api/bt2_schemas.py`, `apps/api/bt2_router.py`, registro en `apps/api/main.py`.
- Referencia de datos demo: mismo espíritu que `apps/web/src/data/vaultMockPicks.ts` (sin acoplar el repo web al importar TS).

#### 4) Contrato de entrada/salida

- Entrada: ninguna en stub (query params reservados para versión futura, p. ej. `operating_day_key`).
- Salida: modelos documentados en OpenAPI (`/docs`).

#### 5) Reglas de dominio

- Regla 1: Ningún campo de respuesta debe incluir **nombres de proveedor** ni DTOs crudos externos.
- Regla 2: `settlement_verification_mode` en stub = **`trust`** hasta existir resultados canónicos CDM en servidor.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given el servidor API en marcha, When se solicita `GET /bt2/meta`, Then la respuesta incluye `contractVersion` y `settlementVerificationMode`.
2. Given el mismo servidor, When se solicita `GET /bt2/vault/picks`, Then la lista tiene ≥ 1 ítem con `selectionSummaryEs` y `marketLabelEs` en español.
3. Given OpenAPI, When un desarrollador abre `/docs`, Then aparecen los esquemas BT2 bajo las rutas anteriores.

#### 7) No funcionales

- CORS ya configurado en `main.py` para orígenes locales Vite.
- Sin dependencias nuevas npm/pip fuera del stack actual.

#### 8) Riesgos y mitigación

- Riesgo: duplicar datos respecto al FE. Mitigación: documentar en `DECISIONES.md`; siguiente sprint puede unificar vía generación o fuente única.

#### 9) Plan de pruebas

- Manual: `curl` o `/docs` contra `GET /bt2/*`.
- Opcional: test ligero con `TestClient` (si se añade en repo).

#### 10) Definition of Done

- [x] T-060, T-061 y T-062 completadas en `TASKS.md`
- [x] `DECISIONES.md` actualizado (stub vs persistencia)
- [x] Servidor arranca sin error de importación

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

**Enmienda producto (2026-04):** eliminar leyenda de token decorativo en el modal del contrato — **US-FE-017**.

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

**Enmienda producto (2026-04):** demo de bóveda con **picks abiertos vs premium** y preview alineada a evento/mercado — **US-FE-023**.

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

- [x] Maquetación y flujo alineados a `us_fe_005_diagnostic.md` (tokens Zurich Calm, sin Material/CDN).
- [x] Cálculo de integridad y perfil en Zustand con tests.
- [x] Guard de diagnóstico validado en el enrutador V2.

**Batch (implementación):** la ruta de foco es `/v2/diagnostic` (no `/v2/sanctuary` hasta completar). Tras contrato, `AuthPage` redirige a diagnóstico si `hasCompletedDiagnostic === false`.

**Enmienda producto (2026-04):** legibilidad del recuadro de vista previa (integridad, estado, DP) — **US-FE-018**.

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
[x] Interfaz implementada según `docs/bettracker2/sprints/sprint-01/refs/us_fe_006_settlement.md` (tokens; sin CDN).

[x] Lógica de liquidación vinculada al useBankrollStore.

[x] Validación de campo de reflexión funcional.

**Batch:** Ruta `/v2/settlement/:pickId`. Cuota mock estable por `pickId` (`pickSettlementMock.ts`). Toast fijo post-confirmación antes de volver a la bóveda.

**Enmiendas posteriores (especificación liquidación / DP):** ver **US-FE-013**.

**Enmienda producto (2026-04):** terminal alineada a **emulación casa de apuestas** (evento, mercado en ES, cuota sugerida vs cuota tomada) — **US-FE-022**.

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
[x] Interfaz implementada según `docs/bettracker2/sprints/sprint-01/refs/us_fe_007_after_action.md` (tokens; sin CDN).

[x] Lógica de reconciliación de saldo operativa.

[x] Bloqueo de UI post-cierre validado.

**Batch:** Ruta `/v2/daily-review`. `closeStationAndFinalizeDay` recibe `settlementsTodayCount` desde la UI (evita ciclo store↔store). Bloqueo 24 h vía `stationLockedUntilIso`. Nota obligatoria si la discrepancia supera el 1 % respecto al proyectado.

**Enmiendas posteriores (día calendario y coherencia con estación):** ver **US-FE-014** y **US-FE-012**.

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
[x] Interfaz implementada según `docs/bettracker2/sprints/sprint-01/refs/us_fe_008_strategic_ledger.md` (tokens; sin CDN).

[x] Filtros y búsqueda funcionales.

[x] Tipado estricto en la interfaz LedgerEntry.

**Batch:** `/v2/ledger` + `LedgerTable`. Protocolo = `marketClass` CDM. Sin virtualización hasta 100 filas (pendiente si crece el volumen).

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
[x] Interfaz implementada según `docs/bettracker2/sprints/sprint-01/refs/us_fe_009_strategy_performance.md` (tokens; sin CDN).

[x] Gráfico de equidad interactivo y filtrable.

[x] Widgets de métricas vinculados al estado global de analíticas.

**Batch:** `/v2/performance` + `EquityChart` (SVG, sin Recharts). Métricas derivadas de `useTradeStore.ledger` vía `ledgerAnalytics.ts`. Sin `useAnalyticsStore` (cálculo en página).

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
[x] Interfaz de perfil implementada con barra de progreso funcional.

[x] Lógica de desbloqueo de diagnóstico validada.

[x] Grid de medallas maquetado con estados bloqueado/desbloqueado.

**Batch:** `/v2/profile` + `RankBadge`. Rango también en cabecera (`BunkerLayout`). Recalibración deshabilitada hasta implementar contador 30 días + 50 ledger (copy visible). Umbrales de rango: Novice / Sentinel / Elite / Master en código.

### US-FE-011 - Cierre de onboarding (fase A) y tour de economía DP (fase B)

#### 1) Objetivo de negocio

Cerrar el blindaje inicial con **reconocimiento claro** y enseñar **cómo funciona la economía de disciplina** antes de que el operador entre en Bóveda operativa, reduciendo frustración ante límites de lecturas gratuitas o costes en DP.

#### 2) Alcance

- Incluye:
  - Tras confirmar **Treasury** con bankroll válido (`US-FE-002`): pantalla o modal de **cierre de fase A** con **un único texto** que enumere hitos completados (sesión/nombre, contrato de disciplina, diagnóstico, capital declarado).
  - **Animación sobria** (p. ej. framer-motion: fade, contador de DP) que muestre el **abono único** de DP de onboarding (valor numérico acordado en economía; referencia `DECISIONES.md` producto onboarding).
  - **Fase B:** flujo corto (2–4 pasos): qué son los DP; **picks abiertos del día** frente a **premium bloqueados**; cómo se **ganan** y **gastan** DP; referencia al **día calendario** (`US-FE-012`).
  - Copy **100 % español**; tipografía datos en **Geist Mono** donde aplique.
- Excluye:
  - Lógica servidor de economía (sigue mock hasta US-BE); calibración final de cifras puede documentarse en `DECISIONES.md`.

#### 3) Contexto técnico actual

- Módulos (previstos): `TreasuryModal` / flujo post-confirm; nuevo componente o ruta p. ej. `OnboardingCompletePage.tsx`, `EconomyTourModal.tsx`; `useUserStore` (flags `hasSeenEconomyTour`, `onboardingPhaseAComplete` si hace falta).
- Decisión de producto: `docs/bettracker2/sprints/sprint-01/DECISIONES.md` (onboarding + economía).

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "treasuryConfirmed": true,
    "hasAcceptedContract": true,
    "hasCompletedDiagnostic": true
  },
  "output": {
    "onboardingPhaseAClosed": true,
    "disciplinePointsGrantOnboarding": 250,
    "economyTourCompleted": true
  }
}
```

*(Los valores numéricos son configurables; el contrato fija forma.)*

#### 5) Reglas de dominio

- Regla 1: El abono de DP de onboarding se otorga **una sola vez** por operador (persistencia); no repetir si reabre el modal de Treasury.
- Regla 2: La fase B no debe bloquear indefinidamente: opción **“Entendido, ir a Santuario/Bóveda”** siempre visible tras el primer paso.
- Regla 3: Estética **Zurich Calm** (`04_IDENTIDAD_VISUAL_UI.md`): sin urgencia artificial. **Excepción explícita:** micro-celebración con partículas acotadas en cierre fase A — ver **US-FE-015**.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given el usuario acaba de confirmar Treasury por primera vez, When se cierra el modal, Then ve el **resumen único** de fase A y el **abono de DP** con animación sobria.
2. Given el usuario completa el tour de economía, When entra a La Bóveda, Then ya ha visto explicación de **lecturas gratuitas diarias** y **desbloqueo con DP**.

#### 7) No funcionales

- Performance: transiciones &lt; 300 ms por paso.
- Observabilidad: `console.info` prefijo `[BT2]` al completar fase A y tour.

#### 8) Riesgos y mitigación

- Riesgo: tour largo → abandono. Mitigación: máximo 4 pasos, progreso visible.

#### 9) Plan de pruebas

- Unitarias: flags de persistencia no duplican grant.
- Manual UI: flujo completo post-onboarding.

#### 10) Definition of Done

- [x] Código implementado
- [x] Tipado estricto
- [x] Tests verdes
- [x] Documentación actualizada en `docs/bettracker2/`
- [x] Sin acoplamiento a proveedor en UI

**Enmiendas de producto:** celebración +250 y copy de logro — **US-FE-015**. Tours por vista — **US-FE-016**.

### US-FE-012 - Día calendario, auto-cierre de sesión disciplinada y gracia 24 h

#### 1) Objetivo de negocio

Alinear la operativa con el **día calendario local**, **reducir estados colgados** (picks sin liquidar, estación sin cerrar) y aplicar **consecuencias auditables** si el operador no completa el protocolo a tiempo, con **gracia** por fuerza mayor.

#### 2) Alcance

- Incluye:
  - Cálculo de **`operatingDayKey`** (fecha local del usuario, TZ configurable en perfil o fallback dispositivo en MVP).
  - Al **cambiar de día calendario** o al **abrir la app**: evaluar pendientes del día anterior (picks activos sin liquidar, estación sin cierre).
  - **Auto-cierre:** cerrar o marcar automáticamente lo que el sistema **pueda** resolver en esa versión (en mock: reglas documentadas + logs `[BT2]`; en vNext: asistencia con **resultado canónico** CDM cuando exista).
  - **Ventana de gracia:** **24 h** tras fin del día calendario para liquidar y/o cerrar estación del día vencido; UI muestra aviso claro (“día anterior pendiente”).
  - Tras gracia: aplicar **tabla de consecuencias** (ver `DECISIONES.md`): p. ej. pérdida de bonos de DP del cierre, penalización de DP, bloqueo temporal de acciones; persistir estado para auditoría.
- Excluye:
  - En MVP mock: no garantizar anti-fraude de cambio de hora del sistema sin **US-BE** (documentar limitación).

#### 3) Contexto técnico actual

- Módulos: `useSessionStore`, `useTradeStore`, `DailyReviewPage`, posible `useDayBoundaryStore` o util `operatingDay.ts`; `SanctuaryPage` avisos.
- Decisión: `docs/bettracker2/sprints/sprint-01/DECISIONES.md` (día calendario + gracia + castigo).

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "userTimeZone": "IANA string",
    "nowIso": "ISO8601"
  },
  "output": {
    "operatingDayKey": "YYYY-MM-DD",
    "previousDayOpenItems": ["UNSETTLED_PICK", "STATION_UNCLOSED"],
    "graceActiveUntilIso": "ISO8601",
    "penaltiesApplied": []
  }
}
```

#### 5) Reglas de dominio

- Regla 1: Topes de DP y “picks del día” usan **`operatingDayKey`**, no solo `stationLockedUntilIso` manual.
- Regla 2: La gracia de 24 h es **por día calendario vencido**, no acumulable infinitamente sin registro (definir máximo de días rezagados en versión futura si aplica).
- Regla 3: Toda penalización debe tener **copy en español** y **motivo** trazable (log o entrada de ledger conductual).

#### 6) Criterios de aceptación (Given / When / Then)

1. Given un cambio de `operatingDayKey` con estación del día anterior sin cerrar, When el usuario abre la app, Then ve **aviso** y puede completar cierre dentro de **24 h** sin penalización plena.
2. Given expirada la gracia con pendientes, When el usuario entra, Then el sistema aplica **consecuencias** documentadas y el estado queda **persistido**.

#### 7) No funcionales

- Observabilidad: eventos `[BT2]` en cambio de día y aplicación de penalizaciones.
- Seguridad: en producción, validación de día en servidor (backlog BE).

#### 8) Riesgos y mitigación

- Riesgo: usuario viaja entre TZ. Mitigación: TZ de perfil explícita en vNext.

#### 9) Plan de pruebas

- Unitarias: cálculo `operatingDayKey` y transición de gracia con reloj inyectado.
- Integración: interacción `useSessionStore` + picks activos.

#### 10) Definition of Done

- [ ] Código implementado
- [ ] Tipado estricto
- [ ] Tests verdes
- [ ] Documentación actualizada en `docs/bettracker2/`
- [ ] Sin acoplamiento a proveedor en UI

### US-FE-013 — [Improvement] respecto a US-FE-006: Modo confianza y evolución a liquidación verificada

#### 1) Objetivo de negocio

Dejar **trazable en producto y código** que el abono de DP por liquidación opera hoy en **modo confianza** (MVP) y podrá evolucionar a **modo verificado** contra el CDM, sin que el ejecutor tenga que inferirlo solo del chat o de `DECISIONES.md`.

#### 2) Alcance

- Incluye:
  - **Constante o configuración explícita** en front (p. ej. `settlementVerificationMode: 'trust'`) documentada y referenciada desde la lógica que abona DP tras liquidación.
  - **Copy breve en español** en la Terminal de liquidación (nota al pie o bloque colapsable) que explique que el cierre es **autodeclarado** en esta fase y que en el futuro podrá validarse contra el **resultado canónico** del evento (`US-DX-001`, `DECISIONES.md` producto liquidación).
  - Comentario de archivo o README de módulo que enlace **US-FE-013** y **US-DX-001**.
- Excluye:
  - Implementar modo `verified` ni consumo de API de resultados (US-BE / vNext).

#### 3) Contexto técnico actual

- Módulos: `SettlementPage.tsx`, `useTradeStore.ts`, posible `apps/web/src/lib/bt2SettlementMode.ts` (nuevo, mínimo).
- US madre: **US-FE-006** (cerrada en alcance original; esta US solo añade improvement de trazabilidad y UX informativa).

#### 4) Contrato de entrada/salida

```json
{
  "config": { "settlementVerificationMode": "trust" },
  "future": { "settlementVerificationMode": "verified" }
}
```

#### 5) Reglas de dominio

- Regla 1: Mientras `settlementVerificationMode === 'trust'`, el flujo y el abono de DP **no cambian** respecto a US-FE-006.
- Regla 2: Ningún texto debe prometer verificación externa hasta que exista US-BE acordada.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given la Terminal de liquidación, When el usuario llega al paso de confirmación, Then ve **explicación en español** del modo confianza (al menos una frase visible sin abrir modal).
2. Given el código de abono de DP, When un desarrollador busca el modo, Then encuentra **una sola fuente de verdad** (`trust`) enlazada a esta US.

#### 7) No funcionales

- Visual: nota al pie acorde a `04_IDENTIDAD_VISUAL_UI.md` (sin alarmismo).
- Observabilidad: opcional `console.info` `[BT2] settlement mode: trust` al liquidar (una vez por sesión o detrás de flag dev).

#### 8) Riesgos y mitigación

- Riesgo: copy largo. Mitigación: texto &lt; 280 caracteres o acordeón.

#### 9) Plan de pruebas

- Manual UI: presencia del copy.
- Unitarias: export del modo sea `'trust'`.

#### 10) Definition of Done

- [ ] Código implementado
- [ ] Tipado estricto
- [ ] Tests verdes
- [ ] Documentación actualizada en `docs/bettracker2/`
- [ ] Sin acoplamiento a proveedor en UI

### US-FE-014 — [Cambio] respecto a US-FE-007: Coherencia estación — día calendario

#### 1) Objetivo de negocio

Alinear el ritual de **cierre de estación** (US-FE-007) con el modelo de **día operativo calendario**, **gracia 24 h** y **auto-cierre** definidos en **US-FE-012** y `DECISIONES.md`, de modo que `stationLockedUntilIso` y los bloqueos de bóveda **no contradigan** el corte por día ni la ventana de gracia.

#### 2) Alcance

- Incluye:
  - Revisión e implementación conjunta con **US-FE-012**: uso de **`operatingDayKey`** (o equivalente) al decidir si la estación del **día vencido** sigue pendiente, si aplica gracia, y cómo interactúa con `stationLockedUntilIso`.
  - Ajuste de reglas en `useSessionStore` (y vistas relacionadas: `DailyReviewPage`, `SanctuaryPage`) para que el copy y el comportamiento digan **“día calendario”** / **“día anterior pendiente”** donde corresponda, en coherencia con US-FE-012.
  - Documentar en código comentario o doc corta la **matriz** bloqueo manual vs corte automático vs gracia.
- Excluye:
  - Redefinir desde cero US-FE-007 sin mantener criterios ya aceptados de reconciliación y score.

#### 3) Contexto técnico actual

- Módulos: `useSessionStore.ts`, `DailyReviewPage.tsx`, `SanctuaryPage.tsx`, integración con trabajo de **US-FE-012**.
- US madre: **US-FE-007**. Dependencia fuerte: **US-FE-012**.

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "operatingDayKey": "YYYY-MM-DD",
    "stationLockedUntilIso": "ISO8601 | null",
    "graceActiveUntilIso": "ISO8601 | null"
  },
  "output": {
    "vaultAccessible": "boolean",
    "userMessageKey": "string"
  }
}
```

#### 5) Reglas de dominio

- Regla 1: El **día operativo** para topes y pendientes es el **día calendario en TZ del usuario** (DECISIONES 2026-04-04).
- Regla 2: `stationLockedUntilIso` y bloqueos de bóveda deben ser **compatibles** con US-FE-012; si hay conflicto, prevalece la tabla de **DECISIONES** tras revisión explícita en PR.
- Regla 3: Copy visible **solo en español**.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given cambio de `operatingDayKey` con estación del día anterior sin cerrar, When el usuario abre el flujo de cierre, Then el sistema guía según **gracia 24 h** (US-FE-012) sin mensajes contradictorios con US-FE-007.
2. Given estación cerrada y bloqueo activo, When aún aplica política de día nuevo, Then la bóveda obedece **una sola** regla coherente documentada.

#### 7) No funcionales

- Tests: casos borde día/DST mínimos en util de fecha si existe.
- Observabilidad: `[BT2]` en transiciones de día que afecten lock.

#### 8) Riesgos y mitigación

- Riesgo: doble bloqueo o bypass. Mitigación: tabla de estados en comentario + test de integración ligero.

#### 9) Plan de pruebas

- Integración: US-FE-012 + US-FE-014 en conjunto.
- Manual: cruce medianoche simulado (dev).

#### 10) Definition of Done

- [ ] Código implementado
- [ ] Tipado estricto
- [ ] Tests verdes
- [ ] Documentación actualizada en `docs/bettracker2/`
- [ ] Sin acoplamiento a proveedor en UI

### US-FE-015 — [Refinement] respecto a US-FE-011: Celebración del abono +250 DP

#### 1) Objetivo de negocio

Reforzar que los **+250 DP** del cierre de fase A son un **reconocimiento ganado** por completar el blindaje inicial, no un saldo anónimo; añadir una **micro-celebración visual** acotada que eleve la emoción sin romper Zurich Calm.

#### 2) Alcance

- Incluye:
  - **Copy** en español que enmarque el logro (p. ej. que el sistema reconoce el compromiso y que los DP se **ganaron** por los cuatro hitos).
  - **Ráfaga de partículas** (confeti sobrio) al finalizar el contador animado hacia +250: paleta **lavanda / menta suave / neutros** (`04_IDENTIDAD_VISUAL_UI.md`), duración **≤ 2,5 s**, **una sola vez** por apertura del modal de fase A.
  - **`prefers-reduced-motion: reduce`:** no reproducir partículas; mantener solo copy + contador.
- Excluye:
  - Confeti en liquidaciones diarias, DP incrementales del header u otros flujos (sigue `04` § feedback de disciplina).
  - Dependencias npm nuevas si se puede lograr con **framer-motion** ya presente.

#### 3) Contexto técnico actual

- `apps/web/src/components/OnboardingCompleteModal.tsx`
- Componente sugerido: `OnboardingConfettiBurst.tsx` (hermano del card, `pointer-events-none`, `z-index` bajo el panel modal).

#### 4) Contrato de entrada/salida

```json
{
  "input": { "counterReachedTarget": true },
  "output": { "celebrationPlayed": true }
}
```

#### 5) Reglas de dominio

- Regla 1: Partículas solo con `counterReachedTarget === true` (fin del contador +250).
- Regla 2: No sonidos obligatorios; opcional silencioso.
- Regla 3: Accesibilidad: `aria-hidden` en capa decorativa; respeto a reduced motion.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given el modal de fase A abierto, When el contador alcanza +250 DP, Then aparece **copy** que comunica logro explícito **y** (si motion OK) **ráfaga breve** de partículas en paleta marca.
2. Given `prefers-reduced-motion: reduce`, When el contador termina, Then **no** hay partículas y el mensaje de logro sigue visible.

#### 7) No funcionales

- Performance: &lt; 40 partículas; sin `requestAnimationFrame` custom pesado.
- Bundle: sin librería de confeti externa salvo decisión en `DECISIONES.md`.

#### 8) Riesgos y mitigación

- Riesgo: sensación “casino”. Mitigación: colores institucionales, sin parpadeo global ni autoplay en bucle.

#### 9) Plan de pruebas

- Manual: abrir fase A en perfil limpio (o reset BT2), ver ráfaga una vez.
- Unitarias: opcional test de que el componente no monta piezas si `reduceMotion` (mock matchMedia).

#### 10) Definition of Done

- [x] Código implementado — `OnboardingConfettiBurst.tsx` + integración en `OnboardingCompleteModal.tsx`
- [x] Tipado estricto
- [x] Tests verdes (regresión modal / store) — 65/65
- [x] Documentación actualizada en `docs/bettracker2/`
- [x] Sin acoplamiento a proveedor en UI

### US-FE-016 — Tours guiados contextuales por vista

#### 1) Objetivo de negocio

Que el operador **entienda cada pantalla** la primera vez (y pueda **reconsultar**) qué hace, qué datos son críticos y **cómo gana o gasta DP** en esa vista, alineado al protocolo conductual.

#### 2) Alcance

- Incluye:
  - **Primera visita:** al entrar por primera vez a cada módulo V2 relevante (Santuario, Bóveda, Liquidación, Cierre del día, Ledger, Rendimiento, Perfil, Ajustes si aplica), ofrecer tour **corto** (2–5 pasos) con foco / tooltip / modal paso a paso coherente con Zurich Calm.
  - **Reapertura:** entrada en menú **“Cómo funciona esta vista”** o icono de ayuda en header contextual que relanza el mismo guion sin duplicar flags de “primera vez” obligatoria.
  - Persistencia por vista: p. ej. `hasSeenTourSanctuary`, `hasSeenTourVault`, … en `useUserStore` o store dedicado `useTourStore` (evaluar tamaño).
  - Copy **español**; mención explícita de **DP** donde la vista tenga economía (Bóveda, Liquidación, Cierre, etc.).
- Excluye:
  - Tours en flujos **focus** ya cubiertos (diagnóstico) salvo que producto pida extensión.
  - Backend: tours 100 % cliente.

#### 3) Contexto técnico actual

- Referencia de patrón: `EconomyTourModal.tsx` (fase B global); US-FE-016 generaliza **por ruta**.
- Módulos: nuevos componentes bajo `apps/web/src/components/tours/` o similar; integración en `BunkerLayout` / páginas.

#### 4) Contrato de entrada/salida

```json
{
  "input": { "routeKey": "sanctuary | vault | settlement | ...", "forceShow": false },
  "output": { "tourCompletedOrDismissed": true }
}
```

#### 5) Reglas de dominio

- Regla 1: Ningún tour bloquea sin **“Saltar”** visible tras el primer paso (misma filosofía que US-FE-011 fase B).
- Regla 2: No repetir automáticamente en cada sesión si `hasSeenTour*` es true; sí bajo `forceShow` desde ayuda.
- Regla 3: Coherencia con **US-FE-012** en vistas que hablen de “día” o gracia (Santuario, Cierre).

#### 6) Criterios de aceptación (Given / When / Then)

1. Given primera visita a La Bóveda, When el usuario entra, Then se ofrece tour que explica **desbloqueo con DP** y (cuando exista en producto) picks abiertos vs premium.
2. Given usuario que ya completó el tour de Santuario, When pulsa “Cómo funciona esta vista”, Then ve de nuevo el guion sin resetear su progresión operativa.

#### 7) No funcionales

- Performance: lazy mount del tour por ruta.
- Accesibilidad: foco atrapado en modal si es modal; `aria-describedby` en pasos.

#### 8) Riesgos y mitigación

- Riesgo: fatiga si demasiados popups. Mitigación: máximo 5 pasos; no encadenar tour global + tour de ruta en el mismo tick.

#### 9) Plan de pruebas

- Integración: navegación entre rutas con flags limpios / sucios.
- Manual: checklist por vista en `QA_CHECKLIST.md` (ampliar).

#### 10) Definition of Done

- [x] Código implementado — 2 vistas piloto: **Santuario** + **La Bóveda** (`ViewTourModal.tsx`, `tourScripts.ts`, `useTourStore.ts`)
- [x] Tipado estricto
- [x] Tests verdes — 65/65
- [x] Documentación actualizada en `docs/bettracker2/`
- [x] Sin acoplamiento a proveedor en UI

**Extensión producto (2026-04):** tours en el resto de rutas V2 — **US-FE-021** (**T-054**, **T-055** en `TASKS.md`).

### US-FE-017 — [Refinement] respecto a US-FE-001: Contrato sin token ficticio

#### 1) Objetivo de negocio

Evitar que el operador interprete como **autenticación real** una leyenda generada en cliente (`SS-VAULT-…`); el contrato debe comunicar solo el compromiso con los tres axiomas, sin ruido técnico innecesario.

#### 2) Alcance

- Incluye:
  - Eliminar del modal **DisciplineContract** el bloque «TOKEN DE AUTENTICACIÓN» y el valor aleatorio asociado.
  - Reorganizar el pie del modal (botón **Confirmar el protocolo** usable, sin columna vacía a la izquierda).
- Excluye:
  - Cambiar reglas de los tres checkboxes, bloqueo del modal ni `onCommitted`.

#### 3) Contexto técnico actual

- `apps/web/src/components/DisciplineContract.tsx` (`makeSessionToken` / estado `sessionToken`).

#### 4) Contrato de entrada/salida

Sin cambio funcional respecto a US-FE-001: `hasAcceptedContract` sigue pasando a `true` tras confirmar con los tres axiomas marcados.

#### 5) Reglas de dominio

- Regla 1: No mostrar identificadores que parezcan credenciales o tokens de API si no lo son.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given el modal del contrato abierto, When el usuario revisa el pie del modal, Then **no** aparece texto «TOKEN DE AUTENTICACIÓN» ni cadena tipo `SS-VAULT-*`.
2. Given los tres axiomas aceptados, When el usuario confirma, Then el flujo de sesión/contrato se comporta igual que antes del cambio.

#### 7) No funcionales

- Estética Zurich Calm; sin nuevas dependencias npm.

#### 8) Riesgos y mitigación

- Riesgo: regresión de layout en móvil. Mitigación: revisar breakpoints del pie del modal.

#### 9) Plan de pruebas

- Manual: Auth → contrato, verificar ausencia de token y CTA visible.
- Unitarias: actualizar si algún test aserta el texto eliminado.

#### 10) Definition of Done

- [x] Código implementado
- [x] Tipado estricto
- [x] Tests verdes en `apps/web`
- [x] Documentación actualizada en `docs/bettracker2/` (esta US + `TASKS.md`)
- [x] Sin acoplamiento a proveedor en UI

### US-FE-018 — [Refinement] respecto a US-FE-005: Diagnóstico — métricas comprensibles

#### 1) Objetivo de negocio

Que un operador sin contexto técnico entienda **qué representa** la vista previa en vivo durante el cuestionario (consistencia de respuestas, señal de estado y puntos de disciplina), alineado al tono Zurich Calm.

#### 2) Alcance

- Incluye:
  - **Integridad:** presentación legible (p. ej. porcentaje entero) y **microcopy** breve que explique que el valor refleja la consistencia de las respuestas en **este** cuestionario (sube con opciones alineadas al protocolo, baja con las más impulsivas). Sin jerga de «servidor» o telemetría opaca.
  - **Estado operador:** sustituir códigos internos visibles (`CALIBRATING_V0`, `STABLE_V4`, `STABLE_V2`, `VOLATILE_PROBE`) por **etiquetas en español** comprensibles; los códigos técnicos no deben ser la única capa visible (opcional `title` para soporte o eliminarlos de UI).
  - **Puntos:** unificar denominación con el producto (**DP**, no «XP» en esa fila) y, si aplica, una línea corta que indique que es **vista previa** del saldo con el ajuste del cuestionario.
- Excluye:
  - Cambiar la fórmula de `integrityAfterAnswer`, `computeOperatorProfile` o `disciplinePointsPreview` salvo decisión explícita de PO (solo presentación y copy).

#### 3) Contexto técnico actual

- `apps/web/src/pages/DiagnosticPage.tsx` (tarjeta de stats junto a perfil; funciones `tierFromIntegrity`, `operatorStatusCode`).
- `apps/web/src/lib/diagnosticScoring.ts` (lógica numérica; referencia, no obligatorio modificar).

#### 4) Contrato de entrada/salida

Igual que US-FE-005 al completar el paso 5 (`assignedProfile`, `systemIntegrity`, persistencia en `useUserStore`).

#### 5) Reglas de dominio

- Regla 1: Copy visible siempre en **español** (`US-FE-005` §7).
- Regla 2: Coherencia de términos con el resto de V2 (**DP**).

#### 6) Criterios de aceptación (Given / When / Then)

1. Given el usuario en una pregunta del diagnóstico, When mira el recuadro de métricas, Then la **integridad** se entiende como indicador del cuestionario (no como dato críptico sin contexto).
2. Given respuestas que cambian el estado, When se actualiza la fila de estado, Then el usuario ve **texto en español**, no solo un código tipo `CALIBRATING_V0`.
3. Given la fila de puntos, When se muestra el valor, Then la unidad es coherente con **DP** en el producto.

#### 7) No funcionales

- Tipografía: datos en Geist Mono donde ya aplica `04_IDENTIDAD_VISUAL_UI.md`; microcopy en sans legible.
- Accesibilidad: si se usa `aria-describedby` / `title`, coherente con el texto visible.

#### 8) Riesgos y mitigación

- Riesgo: párrafos largos. Mitigación: una frase de ayuda por concepto como máximo en el recuadro.

#### 9) Plan de pruebas

- Manual: recorrer las 5 preguntas y verificar textos y transiciones de estado.
- Unitarias: actualizar tests que fijen strings antiguos (`CALIBRATING_V0`, `XP`, etc.).

#### 10) Definition of Done

- [x] Código implementado
- [x] Tipado estricto
- [x] Tests verdes en `apps/web`
- [x] Documentación actualizada en `docs/bettracker2/` (esta US + `TASKS.md`)
- [x] Sin acoplamiento a proveedor en UI

### US-FE-019 — [Refinement transversal] Lectura humana y español en V2 (~90 % identidad)

#### 1) Objetivo de negocio

Acercar la UI V2 al estándar **Zurich Calm** descrito en [`04_IDENTIDAD_VISUAL_UI.md`](../../04_IDENTIDAD_VISUAL_UI.md): operador en **español** y cada métrica crítica acompañada de una **traducción humana** breve (no solo números en monoespaciado).

#### 2) Alcance

- Incluye:
  - **Copy ES:** barrido de textos visibles y accesibles en rutas `/v2/*` (excluir V1 salvo que PO pida); prioridad: headers, CTAs, vacíos, errores.
  - **Patrón dato + línea humana:** en las **tres vistas piloto** acordadas con PO (sugerencia: Santuario, Rendimiento, Perfil), bajo los KPIs definidos en cada pantalla, una línea en Inter que explique *qué significa* o *qué acción sugiere* sin marketing vacío.
- Excluye:
  - Cambiar modelos de datos o APIs; i18n multi-idioma completo (solo ES en este sprint).

#### 3) Contexto técnico actual

- Páginas bajo `apps/web/src/pages/*` y layout `BunkerLayout` / chrome V2.

#### 4) Contrato de entrada/salida

Sin cambio de contratos de negocio; solo presentación y copy.

#### 5) Reglas de dominio

- Regla 1: Tono institucional, sin urgencia artificial (`00_IDENTIDAD_PROYECTO.md`).
- Regla 2: Geist Mono para datos; Inter para la línea humana.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given un recorrido por `/v2/*`, When PO revisa con checklist corto, Then no quedan cadenas de usuario en inglés **obvias** en flujos principales (salvo nombres propios técnicos acordados).
2. Given cada vista piloto, When el usuario lee el bloque de KPI principal, Then existe una **frase corta** que contextualiza el número.

#### 7) No funcionales

- No aumentar densidad visual: una línea por bloque KPI como guía.

#### 8) Riesgos y mitigación

- Riesgo: párrafos largos. Mitigación: límite ~120 caracteres por línea de ayuda salvo PO.

#### 9) Plan de pruebas

- Manual: checklist + capturas opcionales en PR.
- Tests: actualizar snapshots / strings si aplica.

#### 10) Definition of Done

- [x] T-051 y T-052 completadas en `TASKS.md`
- [x] Tests verdes en `apps/web`
- [x] Revisión PO contra `04_IDENTIDAD_VISUAL_UI.md` (registro en `DECISIONES.md`, 2026-04-04)

### US-FE-020 — [Refinement transversal] Semántica de color y tokens (`04`)

#### 1) Objetivo de negocio

Que el color refuerce **significado**: equity/dinero real vs DP/disciplina vs advertencias, según mapa de `04`, reduciendo mezclas que confundan al operador.

#### 2) Alcance

- Incluye:
  - Auditoría dirigida de componentes compartidos y páginas V2 donde convivan verdes, violetas y ámbar.
  - Correcciones acotadas (no rebranding completo).
- Excluye:
  - Nuevo tema oscuro/claro simultáneo si no está en scope.

#### 3) Contexto técnico actual

- Tailwind / clases en `apps/web/src/components/**`, páginas V2.

#### 4) Contrato de entrada/salida

Solo UI.

#### 5) Reglas de dominio

- Regla 1: Emerald/oro sobrio **solo** dinero real y curvas en unidad monetaria donde aplique `04`.
- Regla 2: Accent lavanda para DP y primarios de disciplina, no para P/L monetario.

#### 6) Criterios de aceptación

1. Given las pantallas piloto del barrido, When PO valida, Then no hay violaciones **críticas** documentadas sin ticket de seguimiento o fix en el mismo PR.

#### 7) Plan de pruebas

- Manual + lista de “antes/después” en PR o `DECISIONES.md` (1–3 bullets si hay dudas).

#### 8) Riesgos y mitigación

- Riesgo: regresión visual o pérdida de jerarquía. Mitigación: PR acotado y capturas antes/después.

#### 9) No funcionales

- Sin dependencias nuevas; reutilizar utilidades Tailwind existentes.

#### 10) Definition of Done

- [x] T-053 completada
- [x] Tests verdes
- [x] Nota en `DECISIONES.md` solo si hubo ambigüedad de producto

### US-FE-021 — [Refinement] respecto a US-FE-016: Tours fase 2 (rutas V2 restantes)

#### 1) Objetivo de negocio

Extender el patrón de **US-FE-016** (primera visita + reabrir desde ayuda, `useTourStore`, `ViewTourModal`, `tourScripts`) al resto de módulos V2 que tienen economía DP o cierre de día, sin fatigar (máx. ~5 pasos por vista según US-016).

#### 2) Alcance

- Incluye:
  - **Lote A:** Liquidación, Cierre del día.
  - **Lote B:** Ledger, Rendimiento, Perfil, Ajustes (u orden que defina PO).
- Excluye:
  - Diagnóstico (modo foco ya cubierto); rehacer tours existentes de Santuario/Bóveda salvo bug.

#### 3) Contexto técnico actual

- `apps/web/src/components/tours/*`, `useTourStore`, integración por página como en `SanctuaryPage` / `VaultPage`.

#### 4) Contrato de entrada/salida

Cliente; sin API nueva. Misma semántica que US-FE-016 (`routeKey`, `forceShow` desde ayuda).

#### 5) Reglas de dominio

- Regla 1: **Saltar** visible (US-FE-016 Regla 1).
- Regla 2: No repetir en cada sesión si el flag `hasSeenTour*` está activo; sí al forzar desde ayuda.

#### 6) Criterios de aceptación

1. Given primera visita a una ruta del lote, When entra el usuario, Then se ofrece tour con **Saltar** visible.
2. Given tour ya visto, When pulsa ayuda contextual, Then se relanza el guion sin romper flags.

#### 7) No funcionales

- Lazy mount del modal si el patrón ya existe; copy en español.

#### 8) Riesgos y mitigación

- Riesgo: fatiga por popups. Mitigación: máximo ~5 pasos por vista; no encadenar con otros tours en el mismo tick (US-FE-016 §8).

#### 9) Plan de pruebas

- Manual por ruta; probar flags limpios y usuario que ya completó el tour.

#### 10) Definition of Done

- [x] T-054 y T-055 completadas
- [x] Tests verdes (store / modal si hay cobertura)
- [x] `QA_CHECKLIST.md` o `all_flow_sprint001.md` actualizado con rutas nuevas

### US-FE-022 — [Refinement] respecto a US-FE-006: Liquidación — emulación casa de apuestas

#### 1) Objetivo de negocio

Que la **terminal de liquidación** refleje lo que el operador hace en la casa de apuestas: ver **partido/evento** (identificable), **mercado en español**, **cuota que sugiere el sistema** frente a la **cuota realmente tomada**, y el **capital en riesgo** con el **retorno potencial** si el pick cierra a favor — sin jerga que confunda “precio financiero” con cuota deportiva.

#### 2) Alcance

- Incluye (parte **A**, tarea **T-056**):
  - Ampliar el **CDM mock** del pick (`vaultMockPicks` / tipo): datos mínimos de **evento** visibles en UI (p. ej. `homeTeam`, `awayTeam`, opcional `competition` o `eventLabel` unificado si PO prefiere una sola línea).
  - **Cuota sugerida** explícita en el modelo de dato (decimal europeo), **no** derivada solo de hash del `id` salvo como fallback temporal documentado.
  - **Mapa `marketClass` → etiqueta en español** para todos los valores usados en mocks (p. ej. `ML_TOTAL` → nombre legible tipo “Total goles / más-menos” según tabla acordada en código o `lib/`).
  - En `SettlementPage` (bloque especificación del activo): título de evento **separado** de la **tesis / narrativa del modelo** (`titulo` actual puede quedar como subtítulo “Sugerencia del modelo” o similar).
  - Renombrar **“Precio de entrada”** a copy claro: **“Cuota decimal sugerida”** (o equivalente aprobado por PO).
  - Renombrar la sección **“Traducción humana”** a **“Lectura del modelo”** o **“Sugerencia del sistema”** (elegir uno y unificar); el cuerpo sigue siendo la explicación en prosa (`traduccionHumana` puede renombrarse en código a `modelRationale` en refactor opcional, sin romper persistencia).
  - Pastilla **Mercado**: mostrar **solo** la etiqueta en español (el código CDM puede permanecer en tooltip o `title` para soporte).
- Incluye (parte **B**, tarea **T-057**):
  - Campo de entrada **“Cuota decimal en tu casa”** (u homólogo en español) que el operador completa **antes** o al confirmar la liquidación (definir en implementación: obligatorio para enviar o solo advertencia — por defecto **obligatorio** para alinear a emulación; si PO prefiere MVP suave, advertencia sin bloqueo documentada en PR).
  - **Comparación** cuota sugerida vs cuota casa: estado visual **Alineada / Cercana / Desviada** según umbrales fijos en código (p. ej. diferencia absoluta ≤ 0,02 = alineada, ≤ 0,08 cercana, mayor = desviada) y microcopy que invite a revisar el ticket.
  - **Capital en riesgo** y **retorno potencial** siguen basados en la **unidad de protocolo** (Tesorería) salvo que en la misma tarea se añada campo opcional **“Monto apostado en casa (COP)”**: si existe, usarlo para el preview de PnL de la vista y persistir en el ledger de trade si el modelo de `useTradeStore` lo admite; si no hay tiempo, dejar solo copy que explique que el monto mostrado es la **unidad según protocolo** y el operador debe igualar en la casa.
- Excluye:
  - API real ni scraping de casas; verificación automática de resultado (**US-DX** / **US-BE**).
  - Cambiar **US-FE-013** modo confianza salvo copy transversal mínimo.

**Coordinación:** mismos campos CDM (evento, mercado ES, cuota sugerida, `accessTier` si aplica) que **US-FE-023**; conviene **un solo tipo** compartido y una sola función de mapa de mercado.

#### 3) Contexto técnico actual

- `apps/web/src/pages/SettlementPage.tsx`
- `apps/web/src/data/vaultMockPicks.ts`, `apps/web/src/lib/pickSettlementMock.ts`
- `apps/web/src/lib/settlementPnL.ts`, `apps/web/src/store/useTradeStore.ts`
- Listado en bóveda: alinear etiquetas de mercado/evento **si** el mismo mock alimenta la card (coherencia).

#### 4) Contrato de entrada/salida

Extiende el contrato de **US-FE-006** con campos opcionales persistidos en la entrada de ledger, p. ej. `bookDecimalOdds`, `suggestedDecimalOdds`, `stakeCopEffective` (si se implementa monto casa).

#### 5) Reglas de dominio

- Regla 1: Texto visible al operador **siempre en español** para mercados y labels (códigos CDM solo secundarios).
- Regla 2: La cuota usada para **cálculo de PnL** al liquidar debe ser la **cuota casa** capturada si el campo está completo; si no, mantener cuota sugerida y registrar en comentario de PR/límite conocido.
- Regla 3: No mostrar marcas de proveedores externos en UI.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given un pick desbloqueado, When abre `/v2/settlement/:pickId`, Then ve **equipos o etiqueta de evento** y **mercado en español**, no solo `ML_TOTAL` como única lectura.
2. Given la especificación del activo, When lee la primera fila de datos, Then entiende que el número decimal es **cuota sugerida por el sistema**, no un “precio” de otro dominio.
3. Given el bloque interpretativo, When lee el encabezado, Then no dice “Traducción humana” sino la etiqueta acordada (modelo/sistema).
4. Given el formulario de liquidación, When introduce la cuota de su casa, Then el sistema muestra si está **alineada, cercana o desviada** respecto a la sugerida.
5. Given un resultado ganador, When el operador revisa el preview, Then ve **capital en riesgo** y **retorno bruto potencial** coherentes con las cuotas y monto vigentes (protocolo y/o monto casa si aplica).

#### 7) No funcionales

- Zurich Calm; Geist Mono para cuotas y montos; sin nuevas dependencias npm salvo decisión en `DECISIONES.md`.

#### 8) Riesgos y mitigación

- Riesgo: inflar el formulario. Mitigación: una fila de comparación de cuotas + un campo numérico; umbrales constantes.
- Riesgo: mocks inconsistentes. Mitigación: script o test que liste todos los `marketClass` y exija entrada en el mapa ES.

#### 9) Plan de pruebas

- Unitarias: `settlementPnL` con cuota sugerida vs cuota casa si cambia el cálculo.
- Manual: `v2-p-001` y al menos un pick con otro `marketClass`.
- Actualizar tour de settlement en `tourScripts.ts` si el copy del modal queda obsoleto.

#### 10) Definition of Done

- [x] T-056 y T-057 completadas en `TASKS.md`
- [x] Tests verdes en `apps/web`
- [x] Nota en `DECISIONES.md` si la regla “cuota obligatoria vs advertencia” o los umbrales se fijan como decisión de producto

**Enmienda producto (2026-04):** rótulo **Mercado** explícito + **selección de apuesta** en copy (liquidación/bóveda) — **US-FE-024**.

### US-FE-023 — [Refinement] respecto a US-FE-003: Bóveda — demo abierta/premium y preview de evento

#### 1) Objetivo de negocio

Que la **Bóveda** en MVP mock refleje la economía prevista (**lecturas abiertas vs premium**): un número acotado de señales, con **varias ya accesibles sin sensación de “todo bloqueado”** y **varias premium** que siguen exigiendo DP; y que cada tarjeta muestre **quién juega contra quién** (o etiqueta de evento) y un **resumen del mercado en español**, coherente con la terminal de liquidación (**US-FE-022**).

#### 2) Alcance

- Incluye:
  - **Dataset demo:** reducir o reestructurar el feed mock a **~7 señales** (rango aceptable **6–8**), con **3 o 4 picks “abiertos”** (`accessTier: open` o equivalente) y **2 o 3 “premium”** bloqueados hasta desbloqueo con DP. Eliminar la percepción de “docena+ de cards todas bloqueadas” en estado inicial limpio.
  - **Comportamiento:** los **abiertos** se consideran **desbloqueados para lectura** sin gastar DP (no deben exigir slide de 50 DP para ver la tesis/curva en modo demo); los **premium** mantienen el flujo actual (`tryUnlockPick`, costo **50 DP**, estación no cerrada).
  - **PickCard (preview):** en estado bloqueado y desbloqueado, mostrar **línea de evento** (`homeTeam` vs `awayTeam` o `eventLabel` unificado) y **resumen de mercado en español** (mismo criterio que **US-FE-022**: mapa `marketClass` → copy legible, no solo `ML_TOTAL` en la cara de la card). El título tipo tesis del modelo puede quedar como segunda línea o subtítulo.
  - **Copy:** renombrar en bóveda cualquier **“traducción humana”** visible al usuario por **“Lectura del modelo”** / **“Sugerencia del sistema”** alineado a US-FE-022.
  - **Cabecera:** el contador “N señales disponibles” debe reflejar el nuevo tamaño del mock; opcional chip “X abiertas · Y premium”.
- Excluye:
  - API real ni feed dinámico.
  - Cambiar costo DP ni reglas de estación salvo que choquen con la nueva regla `accessTier` (documentar en `DECISIONES.md` si hay excepción).

#### 3) Contexto técnico actual

- `apps/web/src/data/vaultMockPicks.ts`, `VaultPickCdm`
- `apps/web/src/components/vault/PickCard.tsx`, `apps/web/src/pages/VaultPage.tsx`
- `apps/web/src/store/useVaultStore.ts` — valorar si `isUnlocked` para `open` deriva del tier sin persistir id, o si se pre-seedean ids (preferible lógica explícita por `accessTier` para usuarios con storage sucio).

#### 4) Contrato de entrada/salida

Extiende el CDM del pick con `accessTier: "open" | "premium"` (o nombres acordados) y campos de evento/mercado compartidos con **US-FE-022**.

#### 5) Reglas de dominio

- Regla 1: **Premium** sigue **Regla 1–2** de US-FE-003 (50 DP, disciplina insuficiente).
- Regla 2: **Open** no descuenta DP al “desbloquear” lectura; liquidación solo en picks que el operador haya tomado según reglas existentes de ruta.
- Regla 3: Sin nombres de proveedor en DOM.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given un perfil con estado inicial de bóveda, When abre `/v2/vault`, Then ve **al menos tres** picks abiertos **no** bloqueados como premium y **al menos dos** premium que sí requieren desbloqueo.
2. Given una tarjeta, When lee el preview, Then identifica **evento** (equipos o etiqueta) y **mercado en español** sin depender del código CDM crudo.
3. Given un pick premium sin DP suficiente, When intenta desbloquear, Then el sistema mantiene el mensaje de disciplina insuficiente (US-FE-003).

#### 7) No funcionales

- Grid **6–8** tarjetas: rendimiento trivial; mantener Zurich Calm.

#### 8) Riesgos y mitigación

- Riesgo: usuarios con `unlockedPickIds` antiguos ven mezcla rara. Mitigación: migración de versión en persist o documentar “reset local BT2” en QA.

#### 9) Plan de pruebas

- Unitarias: `PickCard` / helper tier + mapa mercado.
- Manual: vault + entrada a liquidación en un pick abierto desbloqueado para lectura coherente con CDM.

#### 10) Definition of Done

- [x] T-058 completada en `TASKS.md`
- [x] Tests verdes en `apps/web`
- [x] Coordinación con **US-FE-022** en tipo CDM (una sola fuente de verdad para evento + `marketLabelEs` si aplica)

### US-FE-024 — [Refinement] respecto a US-FE-022: Mercado visible y selección de apuesta

#### 1) Objetivo de negocio

Evitar que el operador pase por alto **a qué mercado** corresponde la posición: además del tipo de mercado en español (mapa `marketClass`), debe existir un **rótulo explícito “Mercado”** y, cuando aplique, una **línea de selección** (qué se apuesta en la casa: over/under con línea, lado, hándicap, etc.) coherente con la emulación de ticket deportivo.

#### 2) Alcance

- Incluye:
  - **`SettlementPage`:** encima o junto a la pastilla de tipo de mercado, un label claro **«Mercado»** (misma jerarquía tipográfica que “Cuota decimal sugerida” / micro-labels de la tarjeta).
  - **CDM mock (`VaultPickCdm`):** campo **`selectionSummaryEs`** (string, español), p. ej. «Más de 2.5 goles», «Local -0.5», «Sí en ambos marcan» — **obligatorio en cada pick del mock** actual; si un pick no tiene línea numérica, usar frase corta acorde al `marketClass`.
  - Mostrar **`selectionSummaryEs`** en liquidación (bajo el bloque mercado o en la misma tarjeta de especificación) y en **`PickCard`** (preview, respetando reglas de blur/contenido sensible si US-FE-003 sigue vigente para premium bloqueado).
  - Opcional: persistir `selectionSummaryEs` en entrada de ledger si ya se persisten otros metadatos del pick.
- Excluye:
  - API real; validación contra casa de apuestas automática.

#### 3) Contexto técnico actual

- `apps/web/src/pages/SettlementPage.tsx`, `apps/web/src/components/vault/PickCard.tsx`, `apps/web/src/data/vaultMockPicks.ts`, `apps/web/src/lib/marketLabels.ts` (tipo de mercado; la selección es dato aparte).

#### 4) Contrato de entrada/salida

Extiende `VaultPickCdm` con `selectionSummaryEs: string`; liquidación y bóveda solo lectura desde mock (MVP).

#### 5) Reglas de dominio

- Regla 1: `selectionSummaryEs` siempre en **español**; sin marcas de casa de apuestas.
- Regla 2: Coherente con **US-FE-003** sobre qué se muestra antes del desbloqueo en premium.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given liquidación abierta, When el PO recorre la vista sin tooltip, Then identifica la palabra **Mercado** y el **tipo** y la **selección** sin ambigüedad.
2. Given bóveda, When lee una tarjeta (open o premium según reglas de blur), Then ve **selección** además del nombre del tipo de mercado.

#### 7) No funcionales

- Zurich Calm; no nuevas dependencias npm.

#### 8) Riesgos y mitigación

- Riesgo: textos largos en mobile. Mitigación: máx. ~80 caracteres por `selectionSummaryEs` salvo excepción PO.

#### 9) Plan de pruebas

- Manual: `v2-p-001` y un pick `open` con otro `marketClass`.
- Unitarias: tipo TS del CDM; snapshot opcional de texto si existe.

#### 10) Definition of Done

- [x] T-059 completada en `TASKS.md`
- [x] Tests verdes en `apps/web`
- [x] QA checklist Bloque 12 marcado por PO

## Contratos

### US-DX-001 - Contratos mínimos economía conductual y liquidación (stub)

**Estado:** Stub de lectura **implementado** en `apps/api` bajo **`/bt2/*`** (US-BE-001, T-060–T-062): OpenAPI en `/docs`. Persistencia en BD y modo `verified` siguen **pendientes**.

#### Alcance

- Tipos / OpenAPI futuros para:
  - **`operatingDayKey`**, `userTimeZone`, `graceUntilIso`, flags de sesión por día.
  - **Pick CDM ampliado:** `accessTier: "open" | "premium"`, `unlockCostDp: number`, `operatingDayKey` de pertenencia al feed diario; **US-FE-022 / 023:** `homeTeam` / `awayTeam` (o `eventLabel`), `suggestedDecimalOdds`, `marketClass` + `marketLabelEs`, captura `bookDecimalOdds` en liquidación; **US-FE-023:** demo feed **6–8** filas con mix **open/premium**; **US-FE-024:** `selectionSummaryEs` (línea de apuesta en español).
  - **`settlementVerificationMode`:** `"trust"` (MVP cliente) | `"verified"` (vNext: cruce con resultado canónico del evento).
  - **Resultado canónico** del mercado (referencia por `eventId` / `marketId` CDM, sin nombres de proveedor).

#### Nota

- El modo **verified** y el cierre automático asistido por resultado requieren **US-BE** y fuentes CDM; ver `DECISIONES.md` producto liquidación DP.

## Operacion

### US-OPS-001 - [PENDIENTE]

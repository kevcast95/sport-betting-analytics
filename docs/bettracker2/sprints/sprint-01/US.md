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

## Contratos

### US-DX-001 - [PENDIENTE]

## Operacion

### US-OPS-001 - [PENDIENTE]

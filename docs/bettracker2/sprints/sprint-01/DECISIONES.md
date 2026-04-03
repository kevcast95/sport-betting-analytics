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

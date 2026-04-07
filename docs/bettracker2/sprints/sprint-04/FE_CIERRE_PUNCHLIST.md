# Sprint 04 — Cierre FE: punchlist y inspección manual

Documento de apoyo para **dev FE** (últimos detalles) y **PM/QA** (inspección manual). Fuente técnica: [`HANDOFF_BA_PM_FRONTEND_SPRINT04.md`](../../HANDOFF_BA_PM_FRONTEND_SPRINT04.md) **§8**, [`US.md`](./US.md) US-FE-025…029, [`TASKS.md`](./TASKS.md) **T-111–T-115**.

---

## 1) Resumen ejecutivo

| Área | Estado |
|------|--------|
| Auth JWT + guards V2 | Integrado (`useUserStore`, `bt2FetchJson`) |
| Bóveda | `GET /bt2/vault/picks` tras `POST /bt2/session/open` |
| Bankroll / sesión / settings | Sync post-login (`useAppInit`, stores) |
| Liquidación | `POST /bt2/picks/{id}/settle`; DP **+10** ganado / **+5** perdido (canónico **D-04-011**) |
| Copy / tours / glosario | Alineados a +10/+5; coste vault **50 DP**; sin prometer +25 fijo por “cierre de estación” como regla de servidor |
| Tests web | Ejecutar `npm test` en `apps/web` antes de firmar cierre |

---

## 2) Instruccional dev FE (orden y qué revisar)

**Orden de lectura/implementación histórico:** **026 → 025 → 027 → 028 → 029** (auth antes que vault protegida).

**Antes de dar por cerrado el sprint:**

1. Leer **§8** del HANDOFF (contrato `Bt2VaultPickOut`, `session/open`, vault picks).
2. Confirmar que **`npm test`** en `apps/web` pasa.
3. **Mock (`vaultMockPicks` / fallback settlement):** ✅ resuelto — `SettlementPage.tsx` envuelve el fallback a `vaultMockPicks` en `if (import.meta.env.DEV)`. En producción el mock nunca se activa; en desarrollo sigue disponible para prueba offline.
4. **Ledger / métricas DP:** cualquier default visual para `earnedDp` debe ser coherente con servidor (**preferir `?? 0`**, no asumir 25).
5. **Tours y `EconomyTourModal`:** coste premium **50 DP**; textos de recompensa **+10 / +5** según **D-04-011**.

**Archivos típicos tocados en este cierre:**  
`apps/web/src/hooks/useAppInit.ts`, `store/useVaultStore.ts`, `useTradeStore.ts`, `useUserStore.ts`, `pages/VaultPage.tsx`, `SettlementPage.tsx`, `lib/api.ts`, `components/tours/tourScripts.ts`, `GlossaryModal.tsx`, `EconomyTourModal.tsx`.

---

## 3) Checklist inspección manual (PM)

Ejecutar con **API + web** levantados y usuario de prueba limpio o con DP conocido.

### Autenticación y arranque

- [ ] Registro y login; token persistido; recarga de página mantiene sesión donde corresponda.
- [ ] Tras login, **sync inicial** (bankroll, meta, settings) sin errores en consola de red.

### Sesión operativa y bóveda

- [ ] Ejecutar flujo que abra el día (**`POST /bt2/session/open`** o equivalente UX).
- [ ] Abrir **`/v2/vault`** (o ruta vigente): lista desde API, estados **carga / vacío / error** razonables.
- [ ] Pick **standard**: visible sin consumo de DP (según reglas UI).
- [ ] Pick **premium**: bloqueado hasta saldo ≥ umbral; al desbloquear, refleja **−50 DP** (o coste acordado en settings/backend).

### Liquidación y economía

- [ ] Tras **win**, respuesta/UI muestran **+10 DP** (o valor devuelto por API alineado a D-04-011).
- [ ] Tras **loss**, **+5 DP**.
- [ ] Bankroll y PnL en UI coinciden con **respuesta del servidor** post-`settle`, no solo con estado local previo.

### Contenido y consistencia

- [ ] **Glosario** y **tours** no contradicen la economía canónica (+10/+5, coste premium).
- [ ] No aparece copy obsoleto tipo “+25 por cierre de estación” como hecho garantizado si el backend no lo implementa.

### Regresión rápida

- [ ] Navegación V2 protegida: sin token → comportamiento acordado (login).
- [ ] `npm test` en `apps/web` en verde en la rama que se va a fusionar.

---

## 4) Referencias cruzadas

- DoD FE en [`US.md`](./US.md) (US-FE-025…029): alineado a cierre cuando estas comprobaciones pasan.
- Economía DP: [`DECISIONES.md`](./DECISIONES.md) **D-04-011**.

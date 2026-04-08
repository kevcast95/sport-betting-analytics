# Sprint 05.1 — US

> **Decisiones:** [`DECISIONES.md`](./DECISIONES.md) **D-05.1-001** … **D-05.1-013**.  
> **Tareas:** [`TASKS.md`](./TASKS.md) **T-170–T-187**.  
> **Feedback:** refinement **RFB-02 … RFB-15** (índice y cierres) en [`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md).  
> **Conflictos ID con S6:** **US-FE-040** … **US-FE-049** en esta carpeta — ver [`PLAN.md`](./PLAN.md).

## Resumen

| ID | Capa | Título |
|----|------|--------|
| US-BE-029 | BE | `POST /bt2/vault/premium-unlock` + persistencia; `POST /bt2/picks` sin doble −50 |
| US-FE-040 | FE | Bóveda: slider → unlock API; **Tomar** → `POST /bt2/picks`; badges y guards |
| US-FE-043 | FE | Cabecera V2 unificada; sin «Actualizado ahora»; ayuda «Cómo funciona» *(RFB-01, RFB-10)* |
| US-FE-044 | FE | Bóveda: opacidad/tag post-inicio *(RFB-07)* + premium bloqueado mínimo *(RFB-08)* |
| US-FE-045 | FE | Ledger + Rendimiento: copy honesto clase de mercado, chequeo operativo, banda DP, sin sentimiento ficticio *(RFB-11–13)* |
| US-FE-046 | FE | Santuario: quitar «Santuario Zurich»; recuadro día operativo + CTA cierre *(RFB-02, RFB-03)* |
| US-FE-047 | FE | Glosario: búsqueda en modal *(RFB-04)* |
| US-FE-048 | FE | Sidebar: sincronizar DP con feedback e icono correcto *(RFB-14)* |
| US-FE-049 | FE | V2: auditar y corregir doble fetch en carga *(RFB-15)* |
| US-DX-001-R1 | DX | *(Opcional)* Tipos, `contractVersion`, campo vault si BE lo expone |

---

## Backend

### US-BE-029 — Desacoplar desbloqueo premium de `POST /bt2/picks` *(RFB-09)*

#### 1) Objetivo de negocio

Que el operador **pague el desbloqueo** de la señal premium (ledger `pick_premium_unlock`) y pueda **registrar el pick después** con una segunda acción, sin fila en `bt2_picks` hasta entonces.

#### 2) Alcance

- **Incluye:** **`POST /bt2/vault/premium-unlock`** (ver **D-05.1-002**): cuerpo con identificador estable del ítem de bóveda (p. ej. `vaultPickId` alineado al `id` de `GET /bt2/vault/picks`); transacción que inserta solo movimiento ledger y persistencia de “unlock” para el usuario + día/snapshot acordado; **402** con familia de detalle **D-05-005**; **200** idempotente si ya estaba desbloqueado.
- **Incluye:** **`GET /bt2/vault/picks`:** cada pick premium incluye **`premiumUnlocked: boolean`** (o nombre camelCase acordado en **US-DX-001-R1**) para que el FE no infiera desde ledger.
- **Incluye:** Ajuste **`POST /bt2/picks`:** si el premium ya está desbloqueado para ese criterio, **no** insertar segundo `pick_premium_unlock`; solo crear pick como flujo estándar.
- **Excluye:** DSR, cron, liquidación dual fase B/C, cambio de reglas de settle.

#### 3) Contexto técnico actual

- Módulos: `apps/api/bt2_router.py`, `bt2_schemas.py`, `bt2_models.py`, migración Alembic nueva tabla o columnas mínimas.
- Hoy **US-BE-017** aplica −50 y crea pick en un solo flujo; este US lo separa.

#### 4) Contrato de entrada/salida *(borrador — afinar en implementación)*

**`POST /bt2/vault/premium-unlock`**

```json
{
  "input": {
    "vaultPickId": "string (id CDM del ítem en vault)"
  },
  "output_ok": {
    "vaultPickId": "string",
    "premiumUnlocked": true,
    "dpBalanceAfter": "number | null"
  },
  "errors": {
    "402": "misma familia dp_insufficient_for_premium_unlock (D-05-005)",
    "404": "pick no existe o no es premium / no pertenece al snapshot del usuario",
    "422": "validación body",
    "409": "opcional: conflicto de estado si producto lo define"
  }
}
```

**`Bt2VaultPickOut` (extensión):** campo boolean `premiumUnlocked` (serialization alias coherente con TS).

#### 5) Reglas de dominio

- **R1 — Idempotencia:** segundo `POST` unlock para el mismo `(user, vaultPickId, operatingDayKey)` → **200** sin duplicar ledger.
- **R2 — Elegibilidad:** solo `access_tier = premium` del snapshot del día; saldo ≥ coste (`unlockCostDp` del ítem o constante servidor).
- **R3 — Pick:** `POST /bt2/picks` tras unlock no vuelve a cobrar premium; validar coherencia con evento/mercado del vault.

#### 6) Criterios de aceptación (Given/When/Then)

1. Given usuario con saldo suficiente y premium **no** desbloqueado, When `POST /bt2/vault/premium-unlock`, Then una fila ledger `pick_premium_unlock` y **ningún** `bt2_picks` nuevo para ese compromiso.
2. Given ya desbloqueado, When `POST /bt2/picks` válido, Then **201** y **un** movimiento `pick_premium_unlock` histórico (el del unlock), no un segundo −50.
3. Given saldo insuficiente, When unlock, Then **402** y cuerpo alineado a **D-05-005**.
4. Given `GET /bt2/vault/picks`, When el ítem estaba desbloqueado, Then `premiumUnlocked === true`.

#### 7) No funcionales

- **Performance:** unlock O(1) por usuario; índice en clave de idempotencia.
- **Observabilidad:** log estructurado en unlock y en pick con `vault_pick_id` / `pick_id`.
- **Seguridad:** JWT; no filtrar existencia de picks de otros usuarios (**404** genérico si aplica patrón ACL actual).

#### 8) Riesgos y mitigación

- **Riesgo:** estado persistido vs cliente desincronizado. **Mitigación:** fuente de verdad en GET vault + invalidación FE tras unlock.
- **Riesgo:** migración en entornos con picks premium ya “tomados” en un solo paso. **Mitigación:** script o regla “considerar unlock implícito si ya existe pick abierto para ese vault id” *(definir en T-170)*.

#### 9) Plan de pruebas

- **Integración:** curl unlock → GET vault → POST picks.
- **Manual:** flujo dos pasos en UI tras **US-FE-040**.

#### 10) Definition of Done

- [x] **T-170** cerrada en [`TASKS.md`](./TASKS.md).
- [x] Tests/curl; migración aplicada; sin regresión **V1** `/health`.
- [x] **D-05.1-001** y **D-05.1-002** reflejadas en comportamiento.

---

## Frontend

### US-FE-040 — Bóveda: desbloqueo premium y «Tomar» en dos pasos *(RFB-09)*

#### 1) Objetivo de negocio

Que el slider premium llame **solo** a **`POST /bt2/vault/premium-unlock`** y que **«Tomar pick»** sea un paso aparte que ejecuta **`POST /bt2/picks`**, con copy y badges que no confundan desbloqueo con «En juego».

#### 2) Alcance

- **Incluye:** `useVaultStore` / estado persistido: conjunto o mapa de `vaultPickId` con premium desbloqueado **sincronizado con** `premiumUnlocked` del GET vault al hidratar; separar de `takenApiPicks`.
- **Incluye:** `PickCard`: tras unlock, mostrar contenido premium y CTA **Tomar pick**; badge **«En juego»** solo si hay registro en `takenApiPicks`; toasts distintos (desbloqueo vs registro en protocolo).
- **Incluye:** `VaultPage` / `SettlementPage`: guards **US-FE-033** alineados (liquidación sin pick tomado sigue bloqueada).
- **Excluye:** **RFB-08** (ocultar preview modelo en premium bloqueado) — US aparte si se prioriza.

#### 3) Contexto técnico actual

- `apps/web/src/pages/VaultPage.tsx` — `handleRequestUnlock` / `isApiPickCommitted`.
- `apps/web/src/components/vault/PickCard.tsx` — `SlideToUnlock`, `isUnlocked` prop.
- `apps/web/src/store/useVaultStore.ts` — `takeApiPick`, `takenApiPicks`, `bt2PostPickRegister`.

#### 4) Contrato de entrada/salida

- Consume **US-BE-029** y campos **`premiumUnlocked`** en `Bt2VaultPickOut` (`bt2Types.ts`).

#### 5) Reglas de dominio

- **R1:** Slider premium **no** llama a `takeApiPick` hasta que exista CTA explícita «Tomar» *(salvo que producto unifique copy en un solo botón post-unlock — no es el caso RFB-09)*.
- **R2:** Tras reload, estado desbloqueado debe reconstruirse desde API (GET vault), no solo desde storage local obsoleto.

#### 6) Criterios de aceptación (Given/When/Then)

1. Given premium bloqueado, When el usuario completa el slider, Then se llama unlock API y **no** aparece «En juego» ni **Liquidar** hasta **Tomar**.
2. Given premium desbloqueado y no tomado, When **Tomar**, Then `POST /bt2/picks` y flujo actual post-toma.
3. Given pick ya tomado, When vuelve a la bóveda, Then misma coherencia que hoy para liquidación.

#### 7) No funcionales

- **Compatibilidad:** picks mock / legacy `unlockedPickIds` sin regresión en dev.
- **Accesibilidad:** slider y botón Tomar con `aria-label` claros.

#### 8) Riesgos y mitigación

- **Riesgo:** doble submit. **Mitigación:** estado loading / deshabilitar CTA durante POST.

#### 9) Plan de pruebas

- **Unit:** store y parsers.
- **Manual:** unlock → cerrar pestaña → reabrir → coherencia con GET vault.

#### 10) Definition of Done

- [ ] **T-171**, **T-172** en [`TASKS.md`](./TASKS.md).
- [ ] `npm test` relevantes en verde.

---

### US-FE-043 — Shell V2: cabecera unificada y CTA ayuda *(RFB-01, RFB-10)*

#### 1) Objetivo de negocio

Que todas las vistas del Búnker V2 compartan **la misma lógica de cabecera**: sin marcas temporales falsas, con **«Cómo funciona»** claro y **alineado a la izquierda**, y títulos sin redundancia innecesaria (**D-05.1-003**).

#### 2) Alcance

- **Incluye:** componente reutilizable (p. ej. `BunkerViewHeader` o nombre acordado) con slots: `title`, `subtitle?`, `helpOnClick` / `tourKey`, `rightActions?`; eliminar **«Actualizado ahora»** y variantes.
- **Incluye:** migración de páginas bajo layout V2: **Sanctuary**, **Vault**, **Ledger**, **Performance**, **Profile**, **Daily review**, **Settlement** (y cualquier otra ruta `/v2/*` que hoy repita el patrón).
- **Incluye:** actualización breve [`../../04_IDENTIDAD_VISUAL_UI.md`](../../04_IDENTIDAD_VISUAL_UI.md) §8.
- **Excluye:** cambiar contenido funcional de tours; nuevo endpoint; **RFB-02** (label Santuario) salvo que se absorba visualmente al unificar sin decisión aparte.

#### 3) Contexto técnico actual

- Páginas en `apps/web/src/pages/*` (V2); posible `BunkerLayout` o cabeceras duplicadas por vista.

#### 4) Contrato de entrada/salida

- Props declaradas en TS; sin cambios de API HTTP.

#### 5) Reglas de dominio

- **R1:** Ninguna vista muestra «Actualizado ahora» como texto fijo.
- **R2:** El control de ayuda muestra **icono en círculo** (o equivalente) **antes** del texto «Cómo funciona», alineado al **inicio** del ancho de contenido.

#### 6) Criterios de aceptación (Given/When/Then)

1. Given el usuario recorre las vistas V2 listadas, When compara la parte superior, Then la disposición título / ayuda / acciones sigue el mismo patrón (**D-05.1-003**).
2. Given cualquier vista migrada, When busca «Actualizado ahora», Then no aparece como label decorativo.

#### 7) No funcionales

- **Accesibilidad:** `aria-label` en botón ayuda; foco visible.
- **Responsive:** misma regla de alineación en viewport móvil estándar.

#### 8) Riesgos y mitigación

- **Riesgo:** regresión en una vista olvidada. **Mitigación:** checklist manual en **T-176**; grep en repo del string legacy.

#### 9) Plan de pruebas

- **Manual:** recorrido V2 + screenshot opcional para PO.
- **Automático:** tests de componente si existen; `npm test` global en verde.

#### 10) Definition of Done

- [ ] **T-174**, **T-175**, **T-176** en [`TASKS.md`](./TASKS.md).

---

### US-FE-044 — `PickCard`: RFB-07 (post-inicio) + RFB-08 (premium bloqueado)

#### 1) Objetivo de negocio

Reducir ruido visual y narrativo en la bóveda: picks **no tomables** por hora de inicio se entienden por **estado y opacidad** sin párrafo largo; picks **premium no desbloqueados** muestran solo lo necesario para decidir el pago en DP (**D-05.1-004**, **D-05.1-005**).

#### 2) Alcance

- **Incluye (RFB-07):** `apps/web/src/components/vault/PickCard.tsx` — cuando `takeBlockedAfterStart` (y análogo coherente para premium con slider deshabilitado): quitar copy multilínea; reforzar `article`/`opacity`; tag corto; `title` o tooltip accesible en desktop.
- **Incluye (RFB-08):** mismo archivo — rama `!isUnlocked` + tier premium: eliminar bloque preview `traduccionHumana`, no mostrar `edgeBps`; mostrar cuota sugerida (`suggestedDecimalOdds`) en formato mono; conservar mercado/selección/evento/fecha-hora/slider según **D-05.1-005**.
- **Excluye:** cambiar regla **cuándo** se bloquea toma (sigue **D-05-010** / FE actual); **US-BE-029** / desbloqueo en dos pasos.

#### 3) Contexto técnico actual

- Líneas ~382–421 de `PickCard.tsx` (preview + párrafo largo); header con `edgeBps`.

#### 4) Contrato de entrada/salida

- Sin cambios HTTP; solo presentación.

#### 5) Reglas de dominio

- **R1:** Estándar con post-inicio: **Detalle** puede seguir disponible para revisión (**D-05-010**).
- **R2:** Premium bloqueado: ningún párrafo de “lectura del modelo” antes del desbloqueo.

#### 6) Criterios de aceptación (Given/When/Then)

1. Given pick estándar con inicio ya pasado, When el usuario ve la card, Then **no** aparece el texto largo anterior y ve opacidad + tag (y tooltip en hover donde aplique).
2. Given pick premium bloqueado, When el usuario lee la card, Then **no** hay extracto `traduccionHumana` ni badge edge, y **sí** ve cuota sugerida, fecha/hora y slider.

#### 7) No funcionales

- **Móvil:** cumplimiento sin depender de hover.
- **A11y:** `title` o componente tooltip con foco/teclado si se usa librería existente.

#### 8) Riesgos y mitigación

- **Riesgo:** usuario premium pierde contexto para decidir. **Mitigación:** cuota + evento + hora explícitos en **D-05.1-005**.

#### 9) Plan de pruebas

- **Unit / visual:** casos `takeBlockedAfterStart` true/false; premium locked vs standard locked.
- **Manual:** vault con picks API mock/real.

#### 10) Definition of Done

- [ ] **T-177**, **T-178**, **T-179** en [`TASKS.md`](./TASKS.md).

---

### US-FE-045 — Ledger y Rendimiento: RFB-11, RFB-12, RFB-13 (métricas y nombres honestos)

> **Trazabilidad implementación / rol:** En una sesión **ajena al mandato BA/PM** se aplicaron cambios en `apps/web` (lista en [`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md) § *Alcance del hilo BA/PM y código ya modificado*). Las tareas **T-180–T-182** documentan el trabajo; marcarlas en [`TASKS.md`](./TASKS.md) según DoD del hilo **ejecutor FE**, no asumir cierre solo por existencia de diff.

#### 1) Objetivo de negocio

Evitar que la UI presente **“protocolo”** donde el dato es **clase de mercado**, y evitar **métricas o narrativas** que parezcan oficiales sin fuente (**D-05.1-006** … **D-05.1-008**).

#### 2) Alcance

- **RFB-11 / D-05.1-006:** `LedgerPage.tsx`, `LedgerTable.tsx`, tour `ledger` si aplica — filtro, columna, bloque lateral.
- **RFB-12 / D-05.1-007:** `PerformancePage.tsx`, `tourScripts.ts` (tour `performance`) — subtítulo, tarjeta checklist, pie tesorería.
- **RFB-13 / D-05.1-008:** `PerformancePage.tsx` — card banda DP + **ocultar** bloque “sentimiento global”; ajustar microcopy de KPIs si aún dice “eficiencia del protocolo” de forma ambigua.

#### 3) Criterios de aceptación (Given/When/Then)

1. Given el usuario abre **Ledger**, When lee filtros y tabla, Then no ve “protocolo” usado como nombre del segmento por **marketClass** (sustituido por **clase de mercado** coherente).
2. Given filtra por una clase, When lee el panel lateral, Then entiende que el % es **acierto sobre liquidaciones filtradas**, no una “eficiencia de protocolo” sin definición.
3. Given el usuario abre **Rendimiento**, When ve la columna derecha, Then la tarjeta de checklist **no** incluye un ítem permanentemente verde; el tour **no** habla de “Protocolo Alpha” como marca vacía.
4. Given el usuario ve la banda por DP, When lee el copy, Then queda claro que es **ilustrativo en cliente**; **no** aparece “Sentimiento global” con texto inventado.

#### 10) Definition of Done

- [ ] **T-180**, **T-181**, **T-182** en [`TASKS.md`](./TASKS.md).

---

### US-FE-046 — Santuario: RFB-02 + RFB-03

#### 1) Objetivo

Alinear el Santuario con **cabecera unificada** y con información **operativa real** en lugar de rótulos de marca sueltos o copy vacío.

#### 2) Alcance

- **RFB-02 / D-05.1-009:** `SanctuaryPage.tsx` — eliminar eyebrow **«Santuario Zurich»**.
- **RFB-03 / D-05.1-010:** mismo archivo — sustituir el recuadro **«Estado del entorno»** por resumen de **día operativo**, estación/cierre y gracia según `useSessionStore`, más enlace a **`/v2/daily-review`**; microcopy honesto si falta hidratación.

#### 3) Criterios de aceptación

1. Given el usuario abre **Santuario**, When mira el hero, Then **no** aparece el texto **«Santuario Zurich»**.
2. Given hay `operatingDayKey` o estado de sesión en store, When lee el recuadro operativo, Then ve datos coherentes con la sesión y un CTA claro a cierre del día.
3. Given aún no hay datos, When lee el recuadro, Then ve **—** o equivalente y texto que no simule métricas de proveedor.

#### 10) Definition of Done

- [ ] **T-183**, **T-184** en [`TASKS.md`](./TASKS.md).

---

### US-FE-047 — Glosario: búsqueda *(RFB-04)*

#### 1) Objetivo

Reducir fricción al consultar términos en el modal del glosario.

#### 2) Alcance

- `GlossaryModal.tsx` — input de búsqueda, filtro en cliente, debounce, `aria-label` / label visible.

#### 10) Definition of Done

- [ ] **T-185** en [`TASKS.md`](./TASKS.md).

---

### US-FE-048 — Sidebar: sincronizar DP *(RFB-14)*

#### 1) Objetivo

Que la acción **Sincronizar DP** sea **entendible** y **observable** (éxito y error).

#### 2) Alcance

- `BunkerLayout.tsx` (o componente del control) + `useUserStore.syncDpBalance` — loading, mensaje de error visible, icono distinto de `+`, copy acordado **D-05.1-012**.

#### 10) Definition of Done

- [ ] **T-186** en [`TASKS.md`](./TASKS.md).

---

### US-FE-049 — Doble fetch en carga V2 *(RFB-15)*

#### 1) Objetivo

Eliminar peticiones HTTP duplicadas en la **primera carga** de vistas V2 cuando no estén justificadas por Strict Mode de desarrollo.

#### 2) Alcance

- Auditoría **producción**; lista de rutas en **T-187**; refactors en `useAppInit`, páginas o stores según diagnóstico.

#### 10) Definition of Done

- [ ] **T-187** en [`TASKS.md`](./TASKS.md).

---

## Contratos *(opcional)*

### US-DX-001-R1 — Vault: campo `premiumUnlocked` + tipos *(RFB-09)*

#### 1) Objetivo

Documentar en OpenAPI / TS el boolean en `Bt2VaultPickOut` y el body/response de `POST /bt2/vault/premium-unlock`; bump **`contractVersion`** en meta si el equipo marca cambio visible (**T-173**).

#### 2) Alcance

- **Incluye:** `bt2Types.ts`, `bt2_dx_constants.py` si hay códigos nuevos; alineación camelCase.
- **Excluye:** redefinir catálogo completo **US-DX-001** base.

#### 10) Definition of Done

- [x] **T-173** si **T-170** introduce contrato nuevo o campo vault.

---

*Última actualización: 2026-04-09 — US-FE-046 … US-FE-049 (RFB-02, 03, 04, 14, 15).*

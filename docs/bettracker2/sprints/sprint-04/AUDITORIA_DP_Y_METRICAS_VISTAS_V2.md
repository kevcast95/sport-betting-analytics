# Auditoría V2 — DP y métricas que deben alinearse con la base de datos

**Objetivo:** barrido de vistas y stores bajo `apps/web/src` (rutas `/v2/*`) para listar **qué valores deben ser canónicos del servidor** frente a **hardcode / heurística local / persistencia Zustand que puede desviarse**.

**Audiencia:** Backend (contratos y persistencia) y dev-fe (lectura única de API, eliminación de copy numérico falso).

**Trazabilidad en sprint:** historia **US-FE-030** y tareas **T-119 … T-125** en [`TASKS.md`](./TASKS.md).

**Referencia de producto:** `DECISIONES.md` D-04-011 (DP por liquidación +10/+5); ledger DP en `bt2_dp_ledger`; saldo vía `GET /bt2/user/dp-balance`.

---

## 1. Resumen ejecutivo

| Área | Riesgo principal |
|------|------------------|
| **Saldo DP mostrado** | Mezcla de `syncDpBalance` + `incrementDisciplinePoints` en vault, sesión y liquidación mock → UI puede no coincidir con `SUM(ledger)`. |
| **Tours y modales** | Texto fijo **"1 250 DP"** como “saldo inicial” (captura de pantalla del tour) — **no es el saldo real** del usuario. |
| **Cierre del día / Análisis post-sesión** | ROI, P/L, stake y **“disciplina del día” (52/100)** salen del **ledger local** y fórmulas inventadas; no hay endpoint de “score de disciplina diario”. |
| **Rangos Novato/Sentinel** | Umbrales 1500 / 3000 / 5000 son **reglas de producto en front**; OK si se documentan como UX, pero si el negocio quiere un solo origen, deben venir de settings o tabla. |
| **Coste premium** | API ya envía `unlockCostDp` en vault picks; front aún tiene constante **50** como fallback (`VAULT_UNLOCK_COST_DP`). |
| **Agregados ledger** | `ledgerAnalytics.ts` usa `earnedDp ?? 25` — **discrepancia** con D-04-011 si falta `earnedDp` en fila local. |

---

## 2. Valores que **sí o sí** deben reflejar la DB (o el cálculo servidor)

### 2.1 Saldo total de DP

- **Qué es:** número único de “cuántos DP tengo”.
- **Fuente canónica:** `GET /bt2/user/dp-balance` → `dp_balance` (suma de `bt2_dp_ledger`).
- **Dónde se muestra hoy:** `BunkerLayout` (chip DP), `SanctuaryPage`, `VaultPage` / `PickCard`, `SettlementPage`, `LedgerPage`, `ProfilePage`, `PerformancePage`, flujos de diagnóstico que leen `useUserStore.disciplinePoints`.
- **Gap FE:** Tras tomar pick premium, penalizaciones de gracia y liquidación **mock**, el store ajusta DP con `incrementDisciplinePoints` sin reconciliar siempre con el servidor.
- **Gap BE:** `POST /bt2/picks` no descuenta DP en servidor (el coste premium es solo en front hoy); para coherencia total hace falta **movimiento en ledger** al “take” premium o política explícita documentada.

### 2.2 DP ganados por liquidación (por pick)

- **Qué es:** +10 / +5 / 0 según resultado (D-04-011).
- **Fuente canónica:** respuesta de `POST /bt2/picks/{id}/settle` → `earned_dp`, `dp_balance_after`.
- **Dónde:** filas del ledger en UI, textos de glosario/tours que citan +10/+5 (copy debe coincidir con despliegue).
- **Gap FE:** `finalizeSettlement` / ledger **mock** y `ledgerAnalytics` con fallback `?? 25` distorsionan agregados “DP desde liquidaciones” en Performance/Ledger.

### 2.3 Historial / movimientos de DP (si el producto los muestra)

- **Fuente canónica:** `GET /bt2/user/dp-ledger` (ya existe en API).
- **Gap FE:** Vistas V2 no consumen aún este endpoint de forma principal; el “ledger” de picks es otro concepto (`useTradeStore.ledger`).

### 2.4 Bono onboarding fase A (+250 una vez)

- **Fuente canónica:** `POST /bt2/user/onboarding-phase-a-complete` + fila en `bt2_dp_ledger` con razón acordada.
- **Gap UX:** tours/modales que hablan de “saldo inicial” deben mostrar **saldo real** (`disciplinePoints` tras sync) o **no** prometer un número fijo (p. ej. eliminar “1 250 DP”).

### 2.5 Coste DP al desbloquear pick premium

- **Fuente canónica:** por pick, `unlockCostDp` en `GET /bt2/vault/picks`; umbral mínimo de saldo en `GET /bt2/user/settings` → `dp_unlock_premium_threshold`.
- **Gap FE:** constantes `50` en `useVaultStore`, `PickCard`, `vaultMockPicks` como fallback; deben ser solo respaldo si el API falla, o eliminarse en flujo autenticado.

### 2.6 Penalizaciones por gracia (-50 / -25)

- **Fuente canónica:** hoy **no** está modelado en BE en el flujo que dispara `useSessionStore` (se aplican con `incrementDisciplinePoints` en cliente).
- **Acción BE:** persistir en `bt2_dp_ledger` con razones estables y exponer saldo vía `dp-balance` tras la acción (o endpoint “apply penalties” al cerrar ventana).

---

## 3. Vistas y componentes — inventario

### 3.1 Tour economía DP — `EconomyTourModal.tsx`

| Elemento | Estado | Acción |
|----------|--------|--------|
| Highlight “Tu saldo inicial” **1 250 DP** | Hardcode | **FE:** Sustituir por `disciplinePoints` tras `syncDpBalance` o copy genérico sin número. |
| “50 DP” coste premium | Alineado con constante API típica | **FE:** Preferir valor de settings o primer pick premium del día vía store/API. |
| Texto +10/+5, +250 onboarding | Copy de negocio | **BE/FE:** Mantener alineado con `DECISIONES` y OpenAPI. |

### 3.2 Tours — `tours/tourScripts.ts`

| Elemento | Estado | Acción |
|----------|--------|--------|
| “Sentinel · 1500 DP” | Umbral de **rango** (no saldo) | **Producto:** decidir si umbrales viven en config servidor; si no, documentar como “solo UX”. |
| −50 DP premium | Coherente con D-04 / vault | Misma línea que arriba: idealmente desde settings. |

### 3.3 Glosario — `GlossaryModal.tsx`

| Elemento | Estado | Acción |
|----------|--------|--------|
| Párrafo DP (+10, +5, +250, −50) | Copy estático | **FE:** revisar tras cada cambio de `DECISIONES`; no mostrar cifras que el servidor no aplica aún (p. ej. penalizaciones). |

### 3.4 Cierre del día — `DailyReviewPage.tsx`

| Elemento | Estado | Acción |
|----------|--------|--------|
| Día operativo | `useSessionStore.operatingDayKey` (hidrata API en parte) | **FE:** confirmar siempre desde `GET /bt2/session/day` al entrar. |
| ROI del día, P/L neto, stake, nº liquidaciones | `todaySessionPnlAndStake` / `todayRoiPercent` sobre **ledger local** | **BE:** endpoint “resumen día” desde `bt2_picks` + zona horaria usuario; **FE:** dejar de usar solo memoria local en modo API. |
| **Disciplina del día 52/100** (preview) | Fórmula local (`52 + count*9 + reflexión…`) | **No es DB.** **Producto + BE:** definir si existe score conductual persistido; si no, etiquetar UI como “vista previa local” o eliminar cifra engañosa. |
| Barra ROI púrpura (`roiBarPct`) | Heurística `45 + roiToday*1.8` | Decoración; no requiere DB si se aclara que no es métrica contable. |
| Entradas recientes ledger | Últimas filas `useTradeStore.ledger` | **FE:** en modo API, lista desde `GET /bt2/picks` filtrado por día. |

### 3.5 Layout / navegación — `BunkerLayout.tsx`

| Elemento | Estado | Acción |
|----------|--------|--------|
| Chip DP | `disciplinePoints` | OK si store = API; **FE:** reconciliar tras cada mutación que afecte DP. |
| Rango “Novice / Sentinel / Master” | Umbrales 1500, 3000, 5000 | Ver §2.5 producto vs settings. |
| Botón “Sincronizar DP” | Llama `syncDpBalance` | OK como puente hasta flujo sin drift. |

### 3.6 Perfil — `ProfilePage.tsx`

| Elemento | Estado | Acción |
|----------|--------|--------|
| DP y anillo de progreso al siguiente nivel | `disciplinePoints` + umbrales locales | Igual que rangos: fuente única opcional en BE. |
| Métricas derivadas del ledger local | Mismas que Ledger/Performance | Alinear con API. |

### 3.7 Rendimiento — `PerformancePage.tsx`

| Elemento | Estado | Acción |
|----------|--------|--------|
| “DP acumulados en liquidaciones” | Mezcla `disciplinePoints` global y métricas de `ledgerAnalytics` | **FE:** para coherencia, DP total = API; subtotal por liquidaciones = suma `earned_dp` de filas servidor o de ledger hidratado desde API. |

### 3.8 Libro mayor — `LedgerPage.tsx`

| Elemento | Estado | Acción |
|----------|--------|--------|
| Factor disciplina `dp/150` | Heurística visual | No es DB; renombrar o basar en métrica definida por producto. |
| Lista de filas y `earnedDp` | Store local | **FE:** hidratar desde API; corregir `ledgerAnalytics` fallback `25`. |

### 3.9 Liquidación — `SettlementPage.tsx`

| Elemento | Estado | Acción |
|----------|--------|--------|
| Etiqueta nivel vault (`vaultLevelLabel` con 1500) | Umbral UX | Documentar o externalizar. |
| DP mostrados | `disciplinePoints` | Reconciliar post-`settle`. |

### 3.10 Bóveda — `VaultPage.tsx`, `PickCard.tsx`

| Elemento | Estado | Acción |
|----------|--------|--------|
| Coste premium | API `unlockCostDp` con fallback 50 | **FE:** minimizar fallback; mostrar estado carga/error. |
| Saldo para habilitar botón | `disciplinePoints` | Debe seguir a `dp-balance`. |

### 3.11 Onboarding — `OnboardingCompleteModal.tsx`

| Elemento | Estado | Acción |
|----------|--------|--------|
| Contador +250 | Copy acorde a bono servidor | OK; asegurar que al cerrar se llame endpoint de fase A (ya en diseño reciente). |

### 3.12 Diagnóstico — `DiagnosticPage.tsx` + `diagnosticScoring.ts`

| Elemento | Estado | Acción |
|----------|--------|--------|
| **DP en tarjeta lateral** | **Error de producto:** `disciplinePointsPreview(base, integrity)` altera el número mostrado según **cada respuesta** (`integrity` sube/baja). Eso **no** es el saldo real de DP. | **FE:** Mostrar **solo** `disciplinePoints` sincronizado con API (`GET /bt2/user/dp-balance`). Usuario nuevo → **0** hasta que el ledger/servidor diga otra cosa. **Eliminar** la fórmula `(integrity - DIAGNOSTIC_INITIAL_INTEGRITY) * 400` del valor de DP en UI (o reservarla solo para una métrica distinta si producto la renombra, sin llamarla “Puntos de Disciplina”). Actualizar copy: quitar “refleja el ajuste del cuestionario sobre tu saldo actual” como explicación del DP. |
| Consistencia / integridad del cuestionario | OK como **vista previa** de conducta, separada de DP | No mezclar con el saldo monetario interno DP. |

---

## 4. Checklist por lado

### Backend

1. **Take premium:** decidir e implementar descuento de DP en `bt2_dp_ledger` al registrar pick premium (o documentar que el coste es solo “elegibilidad” sin movimiento hasta otra acción).
2. **Penalizaciones gracia:** persistir −50 / −25 (o valores finales) y reflejar en `dp-balance`.
3. **Resumen diario:** endpoint agregado (PnL, stake, count, opcional score disciplina) por `operating_day_key` y timezone usuario, para reemplazar cálculos solo en cliente en `DailyReviewPage`.
4. **Umbrales de rango (opcional):** `GET /bt2/user/settings` o recurso `protocol/ranks` si el negocio exige un solo origen.
5. **OpenAPI / HANDOFF:** documentar `dp-ledger`, `onboarding-phase-a-complete`, campos de `settle` y costes de vault.

### Frontend (dev-fe)

1. **EconomyTourModal:** eliminar “1 250 DP”; usar saldo en vivo o texto sin cifra inventada.
2. **Tras cada acción que cambie DP:** `syncDpBalance()` o usar siempre `dp_balance_after` de la respuesta (settle, take premium cuando exista BE).
3. **Eliminar drift:** revisar `incrementDisciplinePoints` en `useVaultStore`, `useSessionStore`, `useTradeStore` (mock); sustituir por reconciliación API donde el servidor ya persiste.
4. **`ledgerAnalytics.ts`:** corregir `earnedDp ?? 25` → `?? 0` o valor solo si fila viene del servidor con `earned_dp`.
5. **DailyReview:** hasta tener API, mostrar disclaimer “métricas basadas en datos locales” o deshabilitar cifras que parezcan oficiales (especialmente disciplina 52/100).
6. **PickCard / vault:** usar solo `unlockCostDp` del pick en flujo autenticado; revisar duplicado `VAULT_UNLOCK_COST_DP` en `vaultMockPicks` vs `useVaultStore`.
7. **Diagnóstico:** DP = saldo servidor/store, **no** `disciplinePointsPreview`; ver §3.12.

---

## 5. Referencias de código (ancla rápida)

```41:41:apps/web/src/components/EconomyTourModal.tsx
    highlight: { label: 'Tu saldo inicial', value: '1 250 DP' },
```

```121:124:apps/web/src/pages/DailyReviewPage.tsx
  const previewDisciplineScore = Math.min(
    100,
    Math.round(52 + Math.min(38, count * 9) + (reflection.trim().length >= 24 ? 4 : 0)),
  )
```

```39:44:apps/web/src/lib/ledgerAnalytics.ts
    if (r.outcome === 'PROFIT') wins += 1
    disciplineDpFromSettlements += r.earnedDp ?? 25
  }
```

```19:20:apps/web/src/store/useVaultStore.ts
export const VAULT_UNLOCK_COST_DP = 50
```

---

*Documento generado para handoff PM/BA → BE / dev-fe. Ajustar sprint o `TASKS.md` con tareas explícitas si se prioriza este cierre.*

# Sprint 01 - QA Checklist

**Auditoría de cierre (2026-04-04):** revisión estática frente a `apps/web` + `npm test` (**65 tests**, verdes).

- [x] US cumplen criterios de aceptación (Sprint 01 FE: US-FE-001 … US-FE-024).
- [x] No hay acoplamiento de proveedor en UI.
- [x] No hay acoplamiento de proveedor en dominio (CDM / mocks).
- [x] Tipado estricto y tests verdes (`apps/web`).
- [x] Documentación actualizada en `docs/bettracker2/` (incl. handoff backend: [`../../HANDOFF_BA_PM_BACKEND.md`](../../HANDOFF_BA_PM_BACKEND.md)).
- [ ] **Plan de rollback definido** — **pendiente Sprint 02 / US-OPS** (despliegue, feature flags, reversión de datos).

**Nota PickCard vs orden literal del checklist histórico:** en bóveda el orden visible es **mercado → `selectionSummaryEs` → evento → tesis**, alineado a **US-FE-024** (la selección explícita es requisito de producto). No se considera incumplimiento.

---

## Bloque 9 — Tours y refinamientos +90 % identidad (T-051…T-055)

### Copy español (T-051)
- [x] `/v2/settlement` — botones Ganancia/Pérdida/Empate, badge Recompensa DP, Escudo de disciplina, Tasa de éxito
- [x] `/v2/daily-review` — h1 "Análisis post-sesión"
- [x] `/v2/performance` — Tasa de éxito, Caída máxima
- [x] `/v2/ledger` — filtro "TODOS"

### Patrón métrica + línea humana (T-052)
- [x] `/v2/sanctuary` — línea humana bajo Patrimonio total y bajo Riqueza de carácter
- [x] `/v2/performance` — línea humana bajo ROI, tasa de éxito, caída máxima, DP ganados
- [x] `/v2/profile` — línea humana bajo DP total y Posición global

### Semántica de color (T-053)
- [x] Capital en riesgo → `#914d00` (warning)
- [x] PnL potencial → `#059669` (equity)
- [x] Saldo vault/bankroll → `#059669` (equity)
- [x] P/L neto positivo (daily-review) → `#059669` (equity)
- [x] ROI global → `#059669` (equity)

### Tours contextuales (T-054 + T-055)
- [x] `/v2/settlement` — tour primera visita (botón "Cómo funciona" visible)
- [x] `/v2/daily-review` — tour primera visita (botón "Cómo funciona" visible)
- [x] `/v2/ledger` — tour primera visita (botón "Cómo funciona" visible)
- [x] `/v2/performance` — tour primera visita (botón "Cómo funciona" visible)
- [x] `/v2/profile` — tour primera visita (botón "Cómo funciona" visible)
- [x] `/v2/settings` — tour primera visita (botón "Cómo funciona" visible)
- [x] Tours no se repiten si el flag `hasSeenTour*` está activo
- [x] Botón "Cómo funciona" relanza el tour en cualquier momento

---

## Bloque 10 — Liquidación emulación casa (T-056 + T-057, US-FE-022)

### Especificación del activo (T-056)
- [x] `/v2/settlement/:pickId` — título principal es el `eventLabel` (ej. "Atlético Norte vs Rápidos · Jornada 14")
- [x] Mercado se muestra como etiqueta en español (ej. "Totales (más/menos)"), no `ML_TOTAL`
- [x] "Cuota decimal sugerida" (no "Precio de entrada") toma valor de `suggestedDecimalOdds` del CDM
- [x] Sección interpretativa se llama "Lectura del modelo" (no "Traducción humana")
- [x] Tesis del modelo aparece como "Sugerencia del modelo" (subtítulo)

### Cuota en la casa (T-057)
- [x] Campo "Cuota decimal en tu casa" visible en zona de liquidación
- [x] Al introducir cuota válida: aparece badge Alineada / Cercana / Desviada con microcopy
- [x] Retorno potencial en cabecera usa cuota activa (casa si existe, sugerida si no)
- [x] Modal de confirmación indica qué cuota se usó (sugerida o casa)
- [x] Sin cuota casa: aviso de cuota activa como sugerida (sin bloqueo)
- [x] `LedgerRow` persiste `bookDecimalOdds` y `suggestedDecimalOdds` tras liquidación

---

## Bloque 11 — Bóveda demo abierta/premium (T-058, US-FE-023)

### Feed y tiers
- [x] `/v2/vault` — exactamente 7 picks (3 premium + 4 open)
- [x] Cabecera: "7 señales disponibles · 4 abiertas · 3 premium"
- [x] Picks open (v2-p-004 … v2-p-007): se muestran desbloqueados sin deslizar ni gastar DP
- [x] Picks premium (v2-p-001 … v2-p-003): requieren deslizamiento + 50 DP

### PickCard (T-056/058)
- [x] Chip verde "Abierto" / violeta "Premium" visible en cada tarjeta
- [x] Primera línea de tarjeta: mercado en español (no código CDM)
- [x] `selectionSummaryEs` y `eventLabel` legibles (orden: mercado → selección → evento → tesis; ver nota arriba)
- [x] Tras desbloqueo: sección etiquetada "Lectura del modelo" (no "Traducción humana")
- [x] Cuota sugerida visible tras desbloqueo
- [x] Código CDM aparece solo en `title` del elemento (accesibilidad/debug)

### Migración de persistencia
- [x] Usuario con storage antiguo (v2-p-008 … v2-p-020) no genera errores — IDs huérfanos ignorados
- [x] Reset local en Ajustes limpia el estado correctamente

---

## Bloque 12 — Mercado explícito y selección de apuesta (T-059, US-FE-024)

### SettlementPage
- [x] Encima de la pastilla de tipo de mercado aparece el micro-label **«Mercado»** (mismo estilo tipográfico que "Cuota decimal sugerida")
- [x] Bajo la pastilla se muestra el `selectionSummaryEs` del pick en español (ej. "Más de 218.5 puntos")
- [x] El bloque «Mercado» + tipo + selección es legible sin tooltip ni hover
- [x] Para `v2-p-001` (ML_TOTAL): muestra "Totales (más/menos)" + "Más de 218.5 puntos"
- [x] Para al menos un pick `open` con otro `marketClass` (ej. `v2-p-004` TOTAL_UNDER): "Menos de (Under)" + "Menos de 42.5 puntos"

### PickCard (bóveda)
- [x] Tarjeta **open desbloqueada**: `selectionSummaryEs` visible en el header (zona pública)
- [x] Tarjeta **premium bloqueada**: `selectionSummaryEs` visible en el header (no blurreado — es metadato del pick, no insight del modelo)
- [x] El blur/contenido protegido solo cubre el área inferior (`traduccionHumana` + curva de equity)
- [x] Ninguna tarjeta muestra el código CDM crudo (`ML_TOTAL`, etc.) en la UI visible

### Ledger
- [x] Tras liquidar un pick, `ledger[i].selectionSummaryEs` queda persistido en el store

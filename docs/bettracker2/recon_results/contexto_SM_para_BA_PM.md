# Contexto Sportmonks + The-Odds-API — Para agente BA/PM
**Generado:** 2026-04-05 | **Fuente:** sesión de ejecución Sprint 02 + validación directa de API + docs oficiales

---

## 1. Situación actual del plan Sportmonks

### Plan activo: Pro Trial (14 días)
- **Acceso:** 120 ligas a elección (confirmado vía paginación completa del endpoint `/football/leagues`)
- **API calls:** 3,000 por hora por entidad
- **Créditos consumidos hasta ahora:** ~8 requests de recon (quedan ~2,992)
- **Add-ons incluidos en el trial:** Odds & Predictions + xG & Pressure Index
- **Vencimiento:** 14 días desde la activación del trial Pro

### Estructura de planes post-trial

| Plan | Precio | Ligas | API calls/hora |
|------|--------|-------|----------------|
| Starter | €29/mes | 5 a elección | 2,000 |
| Growth | €99/mes | 30 a elección | 2,500 |
| Pro | €249/mes | 120 a elección | 3,000 |
| Enterprise | Custom | 2,300+ | 5,000 |

**Free plan:** solo 2 ligas fijas (Superliga danesa + Premiership escocesa). Sin odds, sin xG.

### Add-ons disponibles (se suman al plan base)
| Add-on | Precio | Relevancia para BT2 |
|--------|--------|---------------------|
| Odds & Predictions | €15-24/mes | ✅ Crítico para picks en vivo |
| xG & Pressure Index | €24-29/mes | ✅ Crítico para modelo |
| Historical data (>3 temporadas) | €29 one-time | ⚠️ Solo si se quiere ir a 2019-20 |
| Extra leagues | €4/liga/mes | Para añadir ligas fuera del plan base |
| Premium Odds Feed (TXOdds) | €129/mes | ❌ Overkill para BT2 MVP |

---

## 2. Inventario de ligas confirmado (120 ligas en plan Pro)

### Tier S — Hacer sí o sí (top 5 europeas)
| ID | Liga | País |
|----|------|------|
| 8 | Premier League | Inglaterra |
| 82 | Bundesliga | Alemania |
| 301 | Ligue 1 | Francia |
| 384 | Serie A | Italia |
| 564 | La Liga | España |

> **Champions League (ID 2) y UEFA Europa League NO están en el plan actual.**
> Solo están disponibles: AFC Champions League (1085), Copa Libertadores (1122),
> Copa Sudamericana (1116), UEFA Youth League (1329), Europa League Play-offs (1371).

### Tier A — Alta prioridad para el Atraco
| ID | Liga | País | Razón |
|----|------|------|-------|
| 72 | Eredivisie | Países Bajos | Muy bien cubierta por bookmakers europeos |
| 208 | Pro League | Bélgica | Alta liquidez |
| 462 | Liga Portugal | Portugal | Buen volumen |
| 600 | Super Lig | Turquía | Gran liquidez de apuestas |
| 453 | Ekstraklasa | Polonia | Mercado menos eficiente = más edge |
| 501 | Premiership | Escocia | Correlacionada con EPL |
| 672 | Liga BetPlay | Colombia | Relevante para mercado local del usuario |

### Tier B — Si sobran créditos Sportmonks
Championship (9), 2. Bundesliga (85), Ligue 2 (304), Serie B (387), La Liga 2 (567),
MLS (779), Liga MX (743), Liga Profesional Argentina (636), Serie A Brasil (648),
J1 League (968), K League 1 (1034).

### Descartar para el Atraco
- Copas domésticas (24, 27, 78, 109, 307, 390, 468, 570...) — poca muestra, rotación
- Amistosos (1082, 1101, 2450-2452) — sin valor predictivo
- Ligas femeninas (45, 1419, 1583...) — mercado no cubierto por bookmakers
- WC Qualifiers (723, 729) — contexto diferente

---

## 3. Política de datos históricos — aclaración crítica

### Lo que se pensaba vs. lo que es real

**Afirmación validada:** "Los odds solo están disponibles 7 días después del partido."

**Respuesta correcta:** Aplica ÚNICAMENTE al **Premium Odds Feed** (€129/mes, TXOdds).
El Atraco usa el **Standard Odds Feed** — diferente producto, diferente política.

### Standard Odds Feed (lo que usamos)
- Incluido en el add-on Odds & Predictions (€15-24/mes)
- Guarda el **último valor conocido** del odd antes del partido
- **Sin límite de tiempo** para fixtures históricos ya almacenados
- ~50 bookmakers, 150+ mercados
- Actualización cada 1-10 minutos pre-partido
- **No guarda historial de movimientos** (no tienes apertura → cierre, solo el snapshot)
- Para backtesting: suficiente para calcular valor esperado con la cuota representativa

### Premium Odds Feed (NO lo usamos)
- €129/mes extra, partnership TXOdds, 140+ bookmakers, 42 mercados
- Sí guarda historial completo de movimientos (apertura, cambios, cierre)
- **Disponible solo 7 días después del inicio del partido** → luego se elimina
- Para BT2 MVP: overkill. Relevante en Sprint 04+ si se quiere modelar line movement

### Historical data add-on (€29 one-time)
- Aplica a **datos de fixtures** (partidos, estadísticas, eventos), NO a odds
- Desbloquea temporadas anteriores a las últimas 3
- Las últimas 3 temporadas (2022-23, 2023-24, 2024-25) ya están incluidas en todos los planes
- Necesario solo si se quiere ir a 2019-20 o anterior

---

## 4. Rol de The-Odds-API en el Atraco

### ¿Es obligatorio?
No. El Atraco de Sportmonks es autosuficiente para backtesting básico.

### ¿Qué añade The-Odds-API que Sportmonks no da?
| Dimensión | Sportmonks Standard | The-Odds-API |
|-----------|--------------------|----|
| Odds 1X2 pre-partido | ✅ ~50 bookmakers | ✅ ~40 bookmakers EU |
| Snapshot en fecha específica | ⚠️ Solo lo que SM tenía guardado | ✅ Control exacto del timestamp |
| Cobertura LATAM (BetPlay, Liga MX) | ⚠️ Variable | ✅ Mejor cobertura americana |
| Totales (O/U) | ✅ Disponible | ✅ Disponible |
| Asian Handicap | ✅ Disponible | ✅ Disponible |
| Precio | Incluido en add-on activo | $59/mes (100K créditos) |

### Decisión recomendada (para BA/PM)
- **Si el usuario activa The-Odds-API $59/mes:** correr Atraco dual paralelo. Mejor calidad de dato.
- **Si no activa The-Odds-API:** correr solo Sportmonks. Suficiente para MVP de backtesting.
- La tabla `raw_theoddsapi_snapshots` queda vacía pero el schema ya existe para cuando se active.

---

## 5. Estrategia post-Atraco (costos operativos)

### Escenario A — Operación mínima (recomendado post-Sprint 02)
```
Starter €29/mes
  → Elegir: EPL + La Liga + Bundesliga + Serie A + Ligue 1
  → Fixtures, resultados, estadísticas, lineups para picks nuevos

+ Add-on Odds & Predictions €15/mes
  → Odds pre-partido en tiempo real para las 5 ligas
  → Suficiente para validar cuotas de la casa vs. modelo

Total: €44/mes
```

### Escenario B — Con xG en vivo
```
Starter €29 + Odds €15 + xG €24 = €68/mes
→ Modelo completo para picks en vivo
```

### Escenario C — Expandir ligas post-backtesting
```
Growth €99 + Odds €15 + xG €24 = €138/mes
→ 30 ligas, suficiente para cubrir Tier S + A completo
```

---

## 6. Estado del Atraco al momento de este documento

| Ola | Tareas | Estado |
|-----|--------|--------|
| Ola 1 — Configuración entorno | T-075, T-076, T-077, T-078 | ✅ Completa |
| Ola 2 — Schema PostgreSQL | T-069, T-070, T-071 | ✅ Completa |
| Ola 3 — Smoke Test | T-066, T-067, T-068 | ✅ Completa |
| Ola 4 — Atraco Masivo | T-072, T-073, T-074 | ⏳ Pendiente — esperando orden del arquitecto |

### Bloqueantes para Ola 4
1. **Sportmonks:** listo para ejecutar. 2,992 créditos disponibles.
2. **The-Odds-API:** key actual (`d34ede542a7d5cc181ac25e605c2ec9d`) retorna 404 en `/v4/odds` (parón internacional EPL — no hay partidos activos). El endpoint histórico (`/v4/historical/odds`) requiere plan pagado. Si no se activa, el worker de The-Odds-API no producirá datos pero tampoco bloqueará el worker de Sportmonks.

### Configuración acordada para el Atraco
- **Ligas Sportmonks:** Tier S (5) + Tier A selectivo (7-8) = 13 ligas
- **Rango de fechas:** 2021-08-01 a 2025-05-31 (4 temporadas)
- **The-Odds-API sports:** soccer_epl, soccer_spain_la_liga, soccer_germany_bundesliga, soccer_italy_serie_a, soccer_france_ligue_1
- **Paralelismo:** `asyncio.gather(run_sportmonks(), run_theoddsapi())` — workers independientes

---

## 7. Infraestructura levantada (Sprint 02)

| Componente | Estado | Detalle |
|-----------|--------|---------|
| PostgreSQL | ✅ | Postgres.app v18, localhost:5432, DB bettracker2 |
| bt2_settings.py | ✅ | Import seguro — NUNCA en main.py |
| bt2_models.py | ✅ | 3 tablas: raw_sportmonks_fixtures, raw_theoddsapi_snapshots, bt2_event_identity_map |
| Alembic | ✅ | Migración 15ee91ad0d69 aplicada, idempotencia verificada |
| V1 /health | ✅ | Siempre respondiendo {"ok": true} — no afectado |
| Python deps | ✅ | pydantic-settings, sqlalchemy[asyncio], asyncpg, alembic, httpx, psycopg2-binary |

---

*Documento generado al cierre de Ola 3 del Sprint 02. Siguiente paso: ejecutar Ola 4 con instrucción explícita del arquitecto.*

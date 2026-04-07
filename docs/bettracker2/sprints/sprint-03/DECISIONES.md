# Sprint 03 — Decisiones técnicas

> Registro de decisiones arquitectónicas tomadas durante Sprint 03.
> Cada decisión incluye contexto, alternativas descartadas y fecha.

---

## Sprint 03 solo Backend — FE en Sprint 04 (2026-04-07)

- **Decisión:** Sprint 03 cubre únicamente el backend (CDM, Auth, Endpoints reales, Job candidatos). El frontend se conecta en Sprint 04.
- **Motivo:** El backend debe estar sólido y testeado antes de conectar el frontend. Los contratos de API pueden cambiar durante Sprint 03; si el FE se conecta en paralelo, cada cambio de schema rompe el frontend.
- **Impacto:** `apps/web/` no se toca en Sprint 03. Los stubs de `bt2_router.py` se reemplazan gradualmente manteniendo los mismos schemas de respuesta — el frontend sigue funcionando con datos reales sin saber que cambió la fuente.
- **Fecha:** 2026-04-07

---

## CDM normaliza todo excepto exclusiones explícitas (2026-04-07)

- **Decisión:** El normalizador procesa todas las ligas de la BD excepto una lista de exclusión explícita (amistosos, copas menores, ligas femeninas, youth). No hay lista de inclusión — lo desconocido entra con `tier='unknown'` y `is_active=false`.
- **Motivo:** Ya tenemos 88 ligas en BD del Atraco. Una lista de inclusión requeriría mapear manualmente todas — trabajo innecesario. La lista de exclusión es más corta y manejable. Las ligas `unknown` no aparecen en los endpoints de picks (filtradas por `is_active=false`), pero sí están disponibles para análisis posterior.
- **Alternativa descartada:** Lista de inclusión solo con Tier S + A (11 ligas). Demasiado restrictivo — pierde datos útiles del Atraco.
- **Fecha:** 2026-04-07

---

## Schemas de respuesta bt2_router inmutables en Sprint 03 (2026-04-07)

- **Decisión:** Los schemas de respuesta existentes (`Bt2VaultPickOut`, `Bt2SessionDayOut`, `Bt2MetaOut`, `Bt2BehavioralMetricsOut`) no se modifican en Sprint 03. Solo cambia la fuente del dato.
- **Motivo:** El frontend V2 (Sprint 01) ya consume estos contratos. Cambiarlos en Sprint 03 requeriría coordinar con el frontend simultáneamente, lo que viola el principio de "BE primero". Los schemas se pueden enriquecer en Sprint 04 cuando FE y BE se sincronizan.
- **Impacto:** El campo `curva_equidad` en `Bt2VaultPickOut` sigue siendo enviado pero calculado desde datos reales de odds en lugar de hardcodeado.
- **Fecha:** 2026-04-07

---

## JWT con expiración de 7 días, sin refresh token (2026-04-07)

- **Decisión:** Los JWT duran 7 días. No hay endpoint de refresh. El usuario hace re-login al expirar.
- **Motivo:** Para MVP con pocos usuarios conocidos, el refresh token añade complejidad (rotación, almacenamiento seguro, revocación) sin beneficio proporcional. A los 7 días el usuario simplemente vuelve a hacer login.
- **Alternativa descartada:** Refresh tokens (15 min access + 30 días refresh). Correcto para producción con miles de usuarios; overkill para Sprint 03.
- **Costo de revertir:** Bajo — añadir refresh tokens en Sprint 05 sin cambios breaking al frontend (solo añadir endpoint `/bt2/auth/refresh`).
- **Fecha:** 2026-04-07

---

## Job build_candidates.py sin modificar pipeline DSR (2026-04-07)

- **Decisión:** `build_candidates.py` produce archivos JSON en el mismo formato que V1 ya produce para el pipeline DSR. No se modifica ningún job existente de V1.
- **Motivo:** El pipeline DSR (split_ds_batches → deepseek_batches → merge → render → telegram) está probado y corriendo en producción. Cualquier modificación introduce riesgo de romper V1. La Anti-Corruption Layer aquí es el formato de archivo JSON — BT2 lo produce compatible, V1 lo consume sin saber la diferencia.
- **Implicación:** En Sprint 04, cuando BT2 tenga su propia tabla de picks, se puede crear un pipeline DSR dedicado. Por ahora reutiliza el existente.
- **Fecha:** 2026-04-07

---

## Canal de tenis sigue con scraper SofaScore (2026-04-07)

- **Decisión:** Sportmonks no cubre tenis. El canal de tenis (ATP/WTA vía SofaScore) de V1 continúa sin cambios en Sprint 03 y Sprint 04.
- **Motivo:** Migrar tenis a un nuevo proveedor requiere evaluación separada (Tennis Data API, ATP official feed, etc.). No es prioridad mientras el foco sea el modelo de fútbol.
- **Impacto futuro:** En Sprint 05+ se puede evaluar un proveedor de tenis dedicado. Por ahora los picks de tenis siguen siendo de calidad scrapeada, no afecta al modelo de fútbol.
- **Fecha:** 2026-04-07

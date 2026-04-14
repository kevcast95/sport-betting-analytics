# Roadmap PO — norte, capas y qué falta (claridad, no solo técnica)

**Para:** dueño de producto cuando sentís “mucho en el aire”.  
**No sustituye:** `TASKS.md`, `DECISIONES.md` ni el código; **ordena** la cabeza y el orden de batalla.

---

## 1. Tu norte en una frase (reconciliado)

**Querés que el usuario, con rigor, pueda traducir análisis en decisiones de apuesta que mejoren su resultado esperado a lo largo del tiempo**, sin prometer dinero fácil ni fomentar el desborde. El **proceso conductual** es el **cinturón de seguridad**; el **motor** sigue siendo **calidad de dato + señal defendible**. Esos dos ejes no se contradicen: uno sin el otro te deja o con usuarios quemados o con una app “bonita” que no genera confianza estadística.

Si en algún momento el discurso interno solo habla de “conducta” y no de **trazabilidad del acierto del modelo**, o solo de “SM potente” sin **qué mide el admin**, el producto se siente a medias — y es normal que lo sientas así.

---

## 2. Por qué S6–S6.2 “cerrados” igual dejan cosas en el aire

**Cerrar un sprint** en este repo significó, sobre todo: *entregar bloques de software y documentación acordados en ese alcance* (DSR por lotes, bóveda 20/5/5, `ds_input` más rico, disclaimers, admin parcial, etc.).

**No significa automáticamente:**

- que **toda** la potencia de SportMonks ya esté **volcada** al insumo del modelo;
- que el **admin** ya mida la **premisa** que vos tenés en la cabeza (modelo vs bóveda vs resultado real);
- que estén resueltas las **preguntas de producto** (cuánto ve el usuario, cuánto cuesta DSR, cuándo refrescar snapshot);
- que no haya **deuda explícita** (cubo C, FSM Regenerar completo, pool global, actas abiertas) listada en [`../sprint-06.2/CIERRE_S6_2.md`](../sprint-06.2/CIERRE_S6_2.md).

Es decir: **el cierre fue real en ingeniería; la “sensación de cierre total” es otra capa** (visión + métricas + operación). No es que hayas fallado como PO — es que mezclaron dos tipos de “hecho”.

---

## 3. Capas del producto (para ubicar cada problema)

| Capa | Qué es | Si falla o está a medias… |
|------|--------|---------------------------|
| **A. Ingesta / CDM** | SM → Postgres (`bt2_*`, `raw_*`, cuotas, eventos). | El modelo puede ser “bueno en prompt” pero **ciego** o con sesgo 1X2. |
| **B. Insumo al modelo (`ds_input`)** | Qué entra al DSR: consensus, bloques SM opcionales, diagnostics. | Frustración: “SM es potente pero el builder no refleja todo lo que ya pagamos”. |
| **C. Señal (DSR + Post-DSR)** | Lote, reglas, fallback, mezcla de mercados en slate. | Muchos 1X2, poca variedad, o picks que no reflejan el mercado disponible. |
| **D. Snapshot / tiempo** | Cuándo se “congela” la lectura vs cuándo el CDM mejora. | Lineups llegan tarde; vos ves snapshot viejo aunque SM ya tenga más. |
| **E. Experiencia + conducta** | Preview, DP, franjas, cuántos picks ve y desbloquea. | Desborde off-app o percepción de “truco”; no es bug de SM. |
| **F. Medición / admin** | Qué contás como acierto del **modelo** y con qué verdad de resultado. | No podés **cerrar el loop** de mejora ni demostrar rigor al equipo o a vos mismo. |

Los “huecos” que describís encajan sobre todo en **B, D y F**, con **A** como causa raíz a veces (includes, raw, odds incompletas).

---

## 4. Frentes agrupados — alcance, profundidad, impacto

*Impacto:* **Alto** = afecta directamente confianza en la señal o la promesa de negocio. **Medio** = afecta eficiencia, coste o percepción. **Bajo** = higiene o segunda ronda.

### F1 — “¿Qué mide el admin y con qué verdad?” (capa F)

- **Qué es:** Hoy gran parte de “precisión” está atada a **picks liquidados** en app, no al universo **bóveda vs resultado oficial**.  
- **Profundidad:** Decisión de **definición de éxito** + diseño de datos (evaluación por evento/sugerencia).  
- **Alcance:** BE + posible job SM + FE admin.  
- **Impacto:** **Alto** para tu objetivo de rigurosidad y para dejar de dudar con números.  
- **Estado:** Premisa clara en [`premnisa_6.3.md`](./premnisa_6.3.md) §4 y [`Plan_mejora_base.md`](./Plan_mejora_base.md) P2.7; **implementación alineada pendiente**.

### F2 — “¿Usamos SM al nivel que pagamos?” (capas A + B)

- **Qué es:** Includes, `raw` fresco, lineups, más mercados en `bt2_odds_snapshot`, bloques opcionales en `ds_input`. Parte ya está; parte es **deuda** (lineups sin raw, muchos `available: false`, solo 1X2 en muchos eventos).  
- **Profundidad:** Técnica **y** de producto (qué bloques son obligatorios para “Tier A”).  
- **Alcance:** Ingesta, normalización, builder, whitelist DX.  
- **Impacto:** **Alto** para calidad de señal y para tu sensación de “no subutilizar SM”.  
- **Estado:** S6.2 avanzó cubo A; **cierre explícito** de “completitud mínima por liga” **no** está cerrado como regla única.

### F3 — “Snapshot congelado vs datos que mejoran cerca del partido” (capa D)

- **Qué es:** Política de **cuándo** se regenera snapshot / **cuántas** veces DSR / cupos por usuario.  
- **Profundidad:** Trade-off **coste API + LLM** vs frescura.  
- **Alcance:** Jobs, reglas de negocio, quizá solo ingesta frecuente sin re-DSR.  
- **Impacto:** **Alto** en operación y en calidad percibida; **medio** en PnL del negocio (costes).  
- **Estado:** Discutido en [`Plan_mejora_base.md`](./Plan_mejora_base.md); **falta acta numérica** (N refrescos, quién puede).

### F4 — Variedad de mercados y sesgo 1X2 (capa C)

- **Qué es:** Pool con más mercados completos, Post-DSR / desempate, multi-pick por evento **solo** con datos.  
- **Profundidad:** Producto + reglas medibles (“similar soporte”, mix en top K).  
- **Alcance:** BE pool, agregación de odds, posible post-proceso.  
- **Impacto:** **Medio–alto** en robustez de la señal (no solo percepción).  
- **Estado:** [`CONVERSACION_MERCADOS_VARIEDAD_DSR.md`](../../notas/CONVERSACION_MERCADOS_VARIEDAD_DSR.md) + [`premnisa_6.3.md`](./premnisa_6.3.md) §2.

### F5 — Conducta, DP, preview, “20 picks visibles” (capa E)

- **Qué es:** Fricción, desbloqueo, límites por franja; separar **lo que ve el usuario** de **lo que medís en admin**.  
- **Profundidad:** Puramente PO/UX; impacta confianza y riesgo.  
- **Alcance:** FE + reglas economía DP.  
- **Impacto:** **Alto** para promesa ética y sostenibilidad del usuario; **no** sustituye F1–F2.  
- **Estado:** [`premnisa_6.3.md`](./premnisa_6.3.md) §3.

### F6 — Deuda S6.2 explícita (FSM Regenerar, cubo C, pool global, runbooks…)

- **Qué es:** Lista en [`../sprint-06.2/CIERRE_S6_2.md`](../sprint-06.2/CIERRE_S6_2.md) §3.  
- **Impacto:** Variable; **cubo C** alto si querés edge temporal real; **FSM** medio hasta que Regenerar sea crítico en producción.

---

## 5. Roadmap “¿qué necesito para lograr lo que quiero?” (orden recomendado)

No es cronograma de tareas; es **orden de claridad y de palancas**.

### Fase 0 — Congelar la ansiedad (1–2 sesiones contigo o con BA)

1. Escribir **una definición** de éxito del modelo que **no** dependa del usuario liquidando en app (aunque sea v0: “sugerencia bóveda vs 1X2/O-U según mercado elegido”).  
2. Elegir **una** métrica operativa de datos: p. ej. “% de eventos del pool con ≥2 familias de mercado en consensus” (medible en SQL sin LLM).

**Salida:** 1 página que es tu “contrato mental” entre **dinero / rigor / conducta**.

### Fase 1 — Verdad y cierre de loop (prioridad máxima para “rigurosidad”)

- **Impulsar F1** hasta tener **una** vista admin o reporte que refleje **tu** definición (aunque sea manual al principio).  
- En paralelo **F2** con regla mínima: “no entra al pool valor para DSR si…” (completitud acordada).

**Salida:** Dejás de “no entender qué pasa” y pasás a “sé qué falta y cuánto pesa”.

### Fase 2 — Frescura sin quiebrar el banco (F3)

- Política escrita: ingesta SM frecuente vs llamadas DSR.  
- Opcional: medir “tiempo hasta lineups / O-U” en tus ligas piloto.

### Fase 3 — Señal y UX (F4 + F5)

- Variedad de mercados **después** de que el CDM alimente esos mercados.  
- Conducta (DP, preview) alineada a lo que ya medís en F1 (no mezclar “éxito” con “vistas gratis”).

### Fase 4 — Deuda S6.2 según prioridad de negocio (F6)

- Elegir 1–2 ítems del §3 del cierre; el resto queda en backlog explícito.

---

## 6. Confirmación: ¿entiendo la profundidad?

Sí: no es solo “falta un ticket”. Tenés **tres profundidades distintas** mezcladas:

1. **Ingeniería** (qué está mergeado y qué no).  
2. **Producto / definición** (qué es éxito, qué ve el usuario, cuánto cuesta refrescar).  
3. **Rigor estadístico** (verdad de resultado, universo de evaluación, sesgo 1X2).

El síntoma “SM potente pero subutilizado” es en gran parte **B sin reglas de producto cerradas** + **A sin completitud medida**. El síntoma “cerré sprint y sigo perdido” es **F sin implementación alineada a tu premisa**.

---

## 7. Qué **no** hace falta hacer ya para calmarte

- No hace falta **nuevo** modelo local ni más prompts hasta tener **F1** y **completitud mínima** (F2) claras.  
- No hace falta prometer al usuario **más** picks visibles para “demostrar” calidad: eso es **F5** desacoplado de **F1**.

---

## 8. Enlaces rápidos

| Tema | Doc |
|------|-----|
| Cierre técnico S6.2 + traspasos | [`../sprint-06.2/CIERRE_S6_2.md`](../sprint-06.2/CIERRE_S6_2.md) |
| Datos, atraco, odds sin historial | [`../../notas/BACKTESTING_RECONCILIACION_CDM.md`](../../notas/BACKTESTING_RECONCILIACION_CDM.md) |
| Propuestas y preguntas snapshot/DSR/coste | [`Plan_mejora_base.md`](./Plan_mejora_base.md) |
| Premisa mercados, bóveda, admin | [`premnisa_6.3.md`](./premnisa_6.3.md) |
| Plan sprint S6.3 | [`PLAN.md`](./PLAN.md) |

---

*2026-04-12 — documento de apoyo PO; revisar cuando cambie el norte o tras cerrar Fase 0.*

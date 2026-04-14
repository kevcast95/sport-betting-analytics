> Notas sueltas de PO; propuestas y preguntas **estructuradas** (snapshot, DSR, coste, pool): [`Plan_mejora_base.md`](./Plan_mejora_base.md) — §4 deja tabla para **volcar** dudas desde otros docs.  
> **Respuestas BA:** ver subsección al final (2026-04-12); cubre §2–§4 en parte.

1. Cerrar a nivel técnico lo pendiente del S6.2.


2. **Mercados y sesgo 1X2** — Hay un archivo de conversación: [`../../notas/CONVERSACION_MERCADOS_VARIEDAD_DSR.md`](../../notas/CONVERSACION_MERCADOS_VARIEDAD_DSR.md).  
   Ejemplo 12-abr-2026: 20 picks, todos 1X2; 11 aciertos; la mayoría de los 9 restantes en empate; pocos opuestos directos. La variedad no es solo percepción: el modelo puede anclarse a un solo mercado; en parte de los “fallos” 1X2, otro mercado (empate explícito, BTTS, etc.) podría haber calificado distinto según cómo definamos éxito.  
   **Preguntas abiertas (PO/BA):** ¿más de un pick por evento según mercados? ¿sube la varianza? ¿sirve la acotación? ¿distribución objetivo de familias de mercado entre picks generados?

3. **Bóveda, visibilidad y DP** — Si el usuario ve 20 picks completos, nada le impide apostar varios fuera de app sin marcarlos “tomados”. Propuesta: preview mínimo (VS, hora) hasta desbloquear; estándar también con coste en DP (p. ej. 20) y premium (p. ej. 50), en línea con premium hoy. Tensión: limitar desborde vs demostrar que el sistema genera muchos picks con calidad; opción: 1 pick por franja a 20 DP + premium a 50 DP.  
   **Pregunta puntual:** ¿priorizar conducta del usuario o “capacidad de procesamiento / demostración de calidad del modelo”?

4. **Admin — validación global del modelo** — El módulo admin debe poder validar **globalmente** todo lo generado (p. ej. universo de sugerencias de bóveda por día o rango), **monitorear** de forma continua y **concluir** sobre el rendimiento del modelo con métricas alineadas a esa premisa (no sustituidas por “éxito del usuario” ni solo por picks liquidados en app). Encaje con [`../sprint-06.2/CIERRE_S6_2.md`](../sprint-06.2/CIERRE_S6_2.md) §3 (precisión DSR vs picks) y con [`Plan_mejora_base.md`](./Plan_mejora_base.md) P2.7.

---

## Respuestas BA (borrador — no sustituyen acta formal)

### Sobre §2 (varios mercados por evento)

- **¿Más de un pick por evento?** Es viable **solo** si en el `ds_input` de ese evento hay **consensus válido** en esos mercados (O/U, BTTS, etc.). Hoy, si el CDM solo trae 1X2 completo, multi-pick por evento sería forzar lecturas sin soporte en datos → **riesgo de calidad** (ya anotado en la nota de conversación).
- **¿Aumenta la varianza?** Sí en resultados declarados: más mercados = más dimensiones de acierto/error; también **más exposición** del usuario si interpreta como “más señales buenas” sin correlación controlada.
- **¿Sirve la acotación?** Sí: límites por evento (p. ej. máx. 2 familias), por día, y reglas de **diversidad en slate** (ya hay mezcla post-DSR; falta **elegibilidad del pool** con más mercados en CDM).
- **¿Distribución entre picks generados?** Tiene sentido como **objetivo de producto medible** (p. ej. “en el top 5 visible, ≥2 familias distintas cuando el pool lo permita”), no como cuota rígida global si el día es realmente todo 1X2 por datos.

**Prioridad sugerida:** primero **mejorar ingesta + pool** para que existan mercados alternativos en consensus; después **Post-DSR / política de segundo pick** con umbrales explícitos (“similar soporte” → desempate a no-1X2), alineado a `CONVERSACION_MERCADOS_VARIEDAD_DSR.md`.

### Sobre §3 (conducta vs “capacidad del modelo”)

- No compiten en el mismo plano: **conducta** es UX, límites y economía (DP); **capacidad del modelo** se valida en **admin / backtest / muestras internas**, no obligando al usuario final a consumir 20 lecturas completas gratis.
- **Priorizar conducta** en la app pública (fricción, preview bloqueado, cupos por franja) **no** impide medir calidad: medís sobre el **universo generado** (20 en pool, informes, precisión admin) y mostrás al usuario solo lo que la política de riesgo permita.
- **1 pick por franja + premium** es coherente con anti-desborde; la “demostración de riqueza” del sistema puede ser **vista interna** o **modo demo** con copy claro, no acceso ilimitado a texto+cuota+Vektor en 20 filas sin coste.

**Respuesta directa a “¿qué priorizar?”:** Priorizar **conducta y límites claros en producto**; aislar la **validación de calidad del modelo** en instrumentación (admin, métricas por mercado, pool completo) para no mezclar “cuánto ve el user” con “qué tan bueno es el pipeline”.

### Sobre §4 (admin global)

- La premisa de §4 exige **fuente de verdad de resultado** (p. ej. marcador / SM) y **unidad de análisis** = sugerencias del modelo en bóveda (o definición explícita), no solo `bt2_picks` liquidados. Hasta que exista ese pipeline, el admin actual mide **otra** cosa; cerrar US S6.3 para alinear vista + API.
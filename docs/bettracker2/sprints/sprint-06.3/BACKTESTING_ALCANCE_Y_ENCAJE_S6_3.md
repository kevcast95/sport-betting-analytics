# Backtesting — alcance, encaje con roadmap PO y propuesta v1 (Sprint 6.3)

## 1. Propósito de este documento

Este documento integra el tema de **backtesting** dentro del marco definido en `ROADMAP_PO_NORTE_Y_FASES.md`.

La idea no es abrir un proyecto paralelo desordenado, sino dejar claro:

- qué significa backtesting en BetTracker 2.0,
- qué sí conviene construir ahora,
- qué no conviene prometer todavía,
- cómo se conecta con F1, F2 y F3 del roadmap,
- y qué decisiones de producto y datos deben quedar cerradas para hacerlo útil.

---

## 2. Encaje con el norte del producto

El norte reconciliado del proyecto sigue siendo este:

**Permitir que el usuario traduzca análisis en decisiones de apuesta que mejoren su resultado esperado en el tiempo, con rigor, sin vender dinero fácil ni fomentar desborde.**

Desde esa premisa:

- el proceso conductual sigue siendo el cinturón de seguridad;
- el motor sigue siendo calidad de dato + señal defendible;
- y el backtesting entra como herramienta para validar si la señal realmente merece confianza.

**Conclusión:** el backtesting sí tiene sentido ahora, pero como instrumento de verdad y medición, no como tema aislado ni como excusa para postergar F1/F2.

---

## 3. Definición de backtesting para este proyecto

### Definición clara

En BetTracker 2.0, backtesting significa:

**evaluar, con datos históricos, qué habría pasado si el sistema hubiera emitido decisiones en ese momento pasado, usando el insumo disponible, el motor de análisis y las reglas vigentes, y comparando luego esas decisiones contra el resultado oficial.**

No debe definirse solo como “probar un modelo”.
Debe evaluarse el sistema completo:

- universo elegible,
- calidad/completitud del dato,
- construcción de `ds_input`,
- llamada al motor (DSR o equivalente),
- reglas de selección/postproceso,
- y comparación contra resultados oficiales.

---

## 4. Dos modos de backtesting (obligatorio separarlos)

## Modo A — Resultado / calibración

Pregunta que responde:

**“Con el contexto y mercados que le dimos al sistema, habría acertado o no contra el resultado oficial?”**

Este modo mide, por ejemplo:

- hit rate,
- cobertura por ligas,
- cobertura por mercados,
- sesgo 1X2,
- tasa de eventos descartados por falta de datos,
- utilidad del `ds_input`,
- consistencia por ventana temporal.

### Estado actual
Este modo **sí se puede construir ya** con lo que existe.

### Valor
Sirve para:

- cerrar F1 (qué es éxito del modelo),
- apoyar F2 (si realmente estamos usando bien SM),
- y dejar de discutir solo por intuición.

---

## Modo B — Precio / edge temporal

Pregunta que responde:

**“La cuota que el sistema habría usado en ese instante era realmente buena respecto al mercado o al cierre?”**

Este modo busca medir cosas como:

- edge temporal,
- CLV / closing line value,
- eficiencia de la cuota “as of”,
- valor relativo frente a benchmark temporal.

### Estado actual
Este modo **no debe prometerse como serio todavía** con el esquema actual si `bt2_odds_snapshot` sigue representando el último valor ingerido por clave y no un historial congelado o append-only por tiempo.

### Conclusión
Modo B se considera una fase posterior, no el objetivo inicial del backtesting v1.

---

## 5. Recomendación oficial para S6.3

## Sí construir ahora
### Backtesting v1 = Modo A (resultado / calibración)

Este sí debe entrar desde ya, porque ayuda a cerrar claridad de producto y rigor estadístico.

Debe servir para contestar:

- qué tan bien rinde la señal por mercado,
- cuánto del universo realmente es analizable,
- cuánto se subutiliza SM,
- dónde hay sesgo de builder o de pool,
- y si la definición de éxito del modelo es defendible.

## No construir todavía como prioridad
### Backtesting v2 = Modo B (precio / edge temporal real)

Esto queda para después de cerrar una verdad temporal de odds, por ejemplo:

- historial append-only,
- snapshots congelados por corrida,
- o una política explícita de verdad de cuota para experimentos.

---

## 6. Relación directa con el roadmap PO

## F1 — Qué mide el admin y con qué verdad
El backtesting v1 ayuda directamente a F1.

Debe producir una evaluación que no dependa de que el usuario liquide picks dentro de la app.
La unidad de verdad debe tender hacia:

- sugerencia del sistema,
- universo evaluable,
- resultado oficial,
- y eventualmente rendimiento agregado por estrategia.

**Aporte del backtesting a F1:**
- define cómo medir éxito del sistema fuera del uso real del usuario;
- crea base para admin serio;
- reduce ansiedad del PO porque permite ver resultados con un marco fijo.

## F2 — ¿Usamos SM al nivel que pagamos?
El backtesting v1 también ayuda a F2.

No solo importa acertar.
Importa saber:

- cuántos eventos entran con buen dato,
- cuántos quedan fuera,
- qué mercados faltan,
- qué ligas tienen completitud baja,
- y cuánto del poder de SM está realmente reflejado en `ds_input`.

**Aporte del backtesting a F2:**
- vuelve medible la completitud de datos,
- permite comparar builder actual vs builder mejorado,
- expone claramente subutilización de datos.

## F3 — Snapshot / frescura / regeneración
El backtesting v1 no resuelve F3 por sí solo, pero lo prepara.

Porque permite medir:
- si correr más veces cambia materialmente la señal,
- si hay ligas donde lineups/mercados aparecen tarde,
- y si vale la pena pagar una política de refresh más agresiva.

**Conclusión:**
Backtesting v1 entra antes de cerrar toda F3, pero F3 mejora mucho cuando el laboratorio de backtesting ya existe.

---

## 7. Alcance v1 propuesto

El alcance recomendado del backtesting v1 es:

1. Tomar un universo histórico definido.
2. Reconstruir un `ds_input` versionado y reproducible.
3. Ejecutar el motor sobre ese input:
   - idealmente DSR,
   - o un stub reproducible si se quiere separar coste.
4. Guardar picks hipotéticos por corrida.
5. Cruzar cada pick con resultado oficial.
6. Medir desempeño y calidad del universo.

### Universo mínimo sugerido
- fixtures liquidados,
- fechas acotadas,
- ligas definidas,
- mercados explícitos,
- exclusión de eventos con datos claramente insuficientes.

### Importante
No empezar con “todo 2023–2025, todo mercado, toda liga” si eso impide obtener una primera lectura útil.

Mejor arrancar con una ventana defendible y expandir luego.

---

## 8. Salidas mínimas que debe entregar

El backtesting v1 debe producir como mínimo:

- total de eventos evaluados,
- total de eventos descartados,
- motivo de descarte,
- hit rate por mercado,
- hit rate por liga,
- distribución de picks,
- sesgo 1X2,
- cobertura de mercados,
- score de completitud de `ds_input`,
- comparación entre variantes de builder si aplica.

Idealmente también:
- coste estimado por corrida,
- coste por 1000 eventos,
- latencia media,
- y posibilidad de repetir experimento con la misma configuración.

---

## 9. Qué no debe confundirse con backtesting

No confundir backtesting con:

- entrenamiento de un modelo nuevo,
- fine-tuning de un LLM,
- evaluación real de bankroll de usuarios,
- simulación económica completa con stake y gestión avanzada,
- ni prueba definitiva de edge temporal.

Todo eso puede venir después, pero no debe bloquear el arranque del backtesting v1.

---

## 10. Segunda capa antes de DSR

## Sí considerar
Una capa previa barata y medible antes de DSR, por ejemplo:

- reglas de elegibilidad,
- score de completitud,
- ranking de candidatos,
- filtros por mercado/liga/calidad.

Esto puede usar:

- SQL,
- Python,
- features tabulares,
- reglas simples,
- o un modelo clásico si tiene objetivo claro.

## No priorizar todavía
Entrenar un LLM local o montar una capa compleja de IA local como condición para empezar.

Eso hoy sería otro proyecto.
Primero conviene demostrar valor con:

- mejor selección del universo,
- mejor uso de datos,
- menos ruido para DSR,
- y menos coste por evento útil.

---

## 11. Riesgos si se hace mal

### Riesgo 1 — Prometer edge temporal sin verdad temporal
Se genera falsa confianza estadística.

### Riesgo 2 — Correr todo sin definición del universo
Se produce mucho volumen y poca claridad.

### Riesgo 3 — Medir solo hit rate
Se esconde el problema de completitud, cobertura y sesgo.

### Riesgo 4 — Volverlo megaproyecto
Se posterga F1/F2 en lugar de ayudarlas.

### Riesgo 5 — Cambiar builder sin versionado
El experimento deja de ser reproducible.

---

## 12. Decisión recomendada

La recomendación para Sprint 6.3 es esta:

### Decisión
**Sí se incorpora backtesting al roadmap activo, pero solo como backtesting v1 de resultado/calibración, subordinado a F1 y F2.**

### No se promete todavía
- edge temporal serio,
- CLV robusto,
- backtesting de cuota exacta en tiempo,
- ni modelo local entrenado como requisito.

---

## 13. Orden recomendado de ejecución

### Paso 1
Definir universo inicial del backtesting v1.

### Paso 2
Versionar el builder de `ds_input`.

### Paso 3
Definir salida estándar de corrida:
- input version,
- universo,
- fecha de corrida,
- motor usado,
- picks emitidos,
- resultados comparados,
- métricas agregadas.

### Paso 4
Construir primer reporte admin o dataset de evaluación.

### Paso 5
Usar resultados para cerrar:
- definición de éxito del modelo,
- completitud mínima por liga/mercado,
- y prioridad real de mejoras en SM/CDM/builder.

---

## 14. Criterio de éxito de esta iniciativa

Esta iniciativa habrá valido la pena si permite afirmar con más claridad:

- qué tan confiable es hoy la señal,
- dónde estamos subutilizando SM,
- cuánto pesa la completitud del dato,
- y qué mejoras tienen mayor impacto real antes de seguir agregando features.

---

## 15. Resumen ejecutivo

- Sí conviene integrar backtesting desde ya.
- Pero solo en una versión acotada y honesta.
- La prioridad correcta es **Modo A: resultado/calibración**.
- Debe ayudar a cerrar F1 y F2, no competir con ellas.
- El edge temporal y modelos locales entrenados quedan para una fase posterior.

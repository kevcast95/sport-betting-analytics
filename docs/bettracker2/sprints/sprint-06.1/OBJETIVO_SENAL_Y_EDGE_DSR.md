# Objetivo: señal DSR, edge medible y menos ruido (backlog Sprint 06.1)

> **Origen:** resumen de conversación con BE para planificar con PO/BA.  
> **Ejecución prevista:** **Sprint 06.1** — ver [`PLAN.md`](./PLAN.md).  
> **Trazabilidad S6:** **D-06-020** en [`../sprint-06/DECISIONES.md`](../sprint-06/DECISIONES.md).

---

## 1. Objetivo declarado

Priorizar **menos picks con mejor señal**, usando **métricas y reglas medibles** en backend y datos, **no solo** la narrativa o las etiquetas del modelo.

---

## 2. Problema a evitar

Tratar **“Baja / Media / Alta”** (u homólogas) que devuelve el LLM como si fueran:

- **probabilidad de acierto**, o  
- **calidad del feed / ingesta SportMonks**.

Son cosas **distintas**: el modelo puede ser conservador o inconsistente; SportMonks puede estar bien ingestado y aun así el modelo etiquetar “Media”. El producto y analytics deben **no mezclar** esas semánticas en un solo KPI sin definición explícita.

---

## 3. Líneas de trabajo (para planificar juntos)

### 3.1 Elegibilidad dura (datos)

Definir **criterios explícitos de entrada al pool**, por ejemplo:

- **1X2** y **O/U 2.5** presentes en `bt2_odds_snapshot` con los **mismos mapeos** que usa DSR.

Objetivo: lote **homogéneo** y que el modelo compare con la **misma información** por evento.

### 3.2 Volumen (producto / ops)

Acordar **techo de candidatos** y/o **cuota mínima más exigente** en la query del snapshot, para **bajar ruido antes del LLM**.

### 3.3 Edge y umbrales en BE

Especificar si se desea **edge implícito** calculado en servidor (con las odds del input) y **cortes**:

- descartar candidato,  
- degradar a reglas, o  
- marcar **flag** para UI.

Eso acerca “calidad” a algo **auditable** y **repetible** en backtest.

### 3.4 Prompt DSR

Alinear con v1 el mensaje de **“menos picks, más edge”** dentro del lote, pero **subordinado** a los filtros anteriores: **el prompt no sustituye reglas de negocio**.

### 3.5 Semántica en producto

Si hace falta, **separar conceptos** en requisitos explícitos, por ejemplo:

| Concepto | Idea |
|----------|------|
| Completitud de líneas | ¿Tenemos los mercados mínimos en CDM? |
| Confianza modelo | Etiqueta **subjetiva** del LLM (no confundir con P(acierto)). |
| Score dato / edge numérico | Métrica **definida en servidor** (auditable). |

Así UX y analytics **no mezclan** etiquetas sin contrato.

---

## 4. Entregable típico BA con PO

1. **Lista de criterios medibles** (SQL / métricas / checks en job o API).  
2. **Umbrales iniciales** y **criterio de revisión** (cuándo el PO reabre el umbral).  
3. **Impacto esperado** en volumen diario de picks y en **backtesting** (qué tabla de odds se usa como “verdad” en el tiempo — ver nota de reconciliación CDM).

---

## 5. Anexo — enlaces y huecos a rellenar

### 5.1 Documentos relacionados

- [`../../notas/BACKTESTING_RECONCILIACION_CDM.md`](../../notas/BACKTESTING_RECONCILIACION_CDM.md) — atraco vs `fetch_upcoming`, `bt2_odds_snapshot`, implicaciones para backtest.  
- Sprint 06 — contrato DSR / lotes: **D-06-018**, **D-06-019** en [`../sprint-06/DECISIONES.md`](../sprint-06/DECISIONES.md).

### 5.2 US / tareas (rellenar al abrir Sprint 06.1)

| ID | Título | Notas |
|----|--------|--------|
| *(pendiente)* | Elegibilidad pool + SQL | |
| *(pendiente)* | Edge servidor + flags | |
| *(pendiente)* | Prompt + copy semántica UI | |
| *(pendiente)* | Analytics: no mezclar KPIs | |

### 5.3 Umbrales tentativos (solo borrador hasta PO)

| Parámetro | Valor inicial propuesto | Revisión |
|-----------|-------------------------|----------|
| Cuota mínima snapshot | *TBD* | *fecha / owner* |
| Mercados obligatorios | 1X2 + O/U 2.5 | *TBD* |
| Corte edge implícito | *TBD* | *TBD* |

---

*Última actualización: 2026-04-08.*

# Plan mejora base — datos, snapshot, DSR y coste (borrador abierto)

**Estado:** documento **vivo**; decisiones **no** cerradas aquí. Sirve para alinear propuestas y **preguntas** antes de pasar a `DECISIONES.md` / `US.md` del S6.3.

**Relacionado:**

- Nota mercados / sesgo 1X2 y dudas de producto (bóveda, DP, franjas): [`premisa_6.3.md`](./premisa_6.3.md) y [`../../notas/CONVERSACION_MERCADOS_VARIEDAD_DSR.md`](../../notas/CONVERSACION_MERCADOS_VARIEDAD_DSR.md).
- CDM, atraco, odds sin historial temporal: [`../../notas/BACKTESTING_RECONCILIACION_CDM.md`](../../notas/BACKTESTING_RECONCILIACION_CDM.md).
- Cierre S6.2 y traspasos: [`../sprint-06.2/CIERRE_S6_2.md`](../sprint-06.2/CIERRE_S6_2.md).

---

## 1. Problema central (síntesis)

1. **Snapshot de bóveda** = lectura del CDM **en un instante** + (si aplica) **una** pasada DSR; las filas persistidas **no** reflejan solo solas mejoras posteriores en `bt2_odds_snapshot` o en `raw_sportmonks_fixtures` (lineups, etc.).
2. **Acercarse al kickoff** suele mejorar datos en SM/CDM, pero **re-ejecutar DSR** por usuario o en demanda ilimitada **dispara coste** y complejidad operativa.
3. **Pool valor** hoy prioriza tier + proxy de margen; **no** prioriza por “completitud” del insumo (múltiples mercados en consensus, lineups, raw SM presente).
4. **Mercados en `ds_input`:** si la ingesta solo alimenta bien **1X2**, el modelo y las métricas quedan sesgados hacia 1X2 aunque el prompt pida variedad.

---

## 2. Propuestas (para discutir; ninguna es decisión hasta acta)

### P2.1 — Separar frescura CDM de frescura DSR

- **Ingesta frecuente (barata):** `fetch_upcoming` / jobs que actualicen `bt2_odds_snapshot` y, según política, `raw_sportmonks_fixtures`.
- **DSR acotado (caro):** reglas explícitas: máximo N regeneraciones por `operating_day_key` y usuario, o ventanas fijas (p. ej. matutina + pre-franja), o solo si cambió hash de `ds_input` relevante.

### P2.2 — Elegibilidad del pool por “completitud”

- Añadir **score** o **filtro duro**: p. ej. exigir 1X2 + O/U 2.5 en consensus, o ponderar eventos con más mercados completos y/o `lineups.available` antes de entrar al universo ~20.
- Alinear con la tabla de palancas en `BACKTESTING_RECONCILIACION_CDM.md` §4.

### P2.3 — Medición empírica “¿cuándo está completo el dato?”

- Job o consulta que registre, por liga/fixture, **tiempo hasta** primera aparición de lineups / mercados clave; alimentar **p50/p90** para decidir ventanas de snapshot (sin afirmar promedios globales sin datos).

### P2.4 — Pool global + vista por usuario (deuda ya citada en inventario S6.2)

- Un **lote DSR** por ventana/día reutilizable reduce llamadas si muchos usuarios comparten el mismo análisis base.

### P2.5 — Variedad de mercados en picks (producto + modelo)

- Explorar **más de un pick por evento** (distintos mercados), **cuotas** de familia por slate, o **forzar** diversidad en Post-DSR — con análisis de varianza y de UX (ver `premisa_6.3.md` y nota de conversación).

### P2.6 — Conducta de usuario vs visibilidad de picks (DP, bloqueo, premium)

- Acotar “20 visibles / switch” frente a **fricción real** (solo preview mínimo hasta desbloquear, coste DP por estándar/premium, 1 pick por franja, etc.) — línea ya esbozada en `premisa_6.3.md`.

### P2.7 — Admin precisión alineada a “modelo en bóveda”

- Evaluación contra resultado oficial **sin depender** solo de picks liquidados por usuario (traspaso desde cierre S6.2).

---

## 3. Preguntas abiertas (checklist para BA / PO / datos)

Marcar `[ ]` → `[x]` cuando haya respuesta documentada (en `DECISIONES.md` o anexo).

### 3.1 Snapshot y tiempo

- [ ] ¿Cuántas **regeneraciones** de snapshot por usuario y día operativo son aceptables (0 / 1 / 2 / ilimitado con cupo)?
- [ ] ¿Se permite **re-DSR** sin regenerar todo el snapshot (solo subset de eventos)?
- [ ] ¿El producto prefiere **lectura temprana** (más tiempo para decidir) o **lectura tardía** (mejor insumo)? ¿Depende de **tier** de usuario o de liga?

### 3.2 Coste y límites

- [ ] Presupuesto mensual **objetivo** (tokens / llamadas) para DSR en producción.
- [ ] ¿Quién puede forzar refresh: solo **admin**, solo **cron**, usuario **premium**?
- [ ] ¿SM se consulta **solo** en jobs batch o también **on-demand** por evento (riesgo de cuota de API)?

### 3.3 Completitud de datos

- [ ] ¿Qué significa **“evento elegible”** en v1 de la regla: solo 1X2, o 1X2 + O/U 2.5, o + BTTS?
- [ ] ¿Se **excluyen** eventos sin `raw` SM aunque tengan cuotas?
- [ ] ¿Lineups son **obligatorios** para Tier A o solo “nice to have”?

### 3.4 Variedad de mercados y picks

- [ ] ¿Más de **un pick por evento** (mercados distintos) entra en alcance? ¿Límite por evento y por día?
- [ ] ¿Objetivo explícito de **mix** en el slate visible (p. ej. mínimo 2 familias distintas)?

### 3.5 Conducta y economía (DP)

- [ ] ¿Todos los picks estándar en preview **bloqueados** hasta DP? ¿Mismo tratamiento que premium salvo precio?
- [ ] ¿Un pick **por franja** + un premium global reemplaza el modelo “20 en carrusel”?
- [ ] ¿Cómo se **audita** apuesta fuera de app sin romper la promesa de “anti-desborde”?

### 3.6 Atraco e historial

- [ ] ¿Prioridad de **tablas agregadas** (p. ej. stats de temporada por equipo) frente a lectura ad-hoc del `raw`?
- [ ] ¿Se necesita **historial de cuotas** (cubo C) antes de prometer edge temporal en admin?

---

## 4. Volcado desde otro documento de dudas (pendiente)

*Aquí se pegarán o listarán las preguntas adicionales cuando estén en un archivo aparte; mantener numeración aparte (4.x) o referenciar archivo + ítem.*

| # | Pregunta / duda (texto libre) | Respuesta / decisión | Enlace acta |
|---|------------------------------|----------------------|-------------|
| 4.1 | Variedad de mercados, multi-pick por evento, varianza, acotación, distribución (`premnisa_6.3` §2) | Borrador BA en [`premnisa_6.3.md`](./premnisa_6.3.md) § “Respuestas BA” | Pendiente PO |
| 4.2 | Bóveda: preview bloqueado, DP estándar/premium, conducta vs validación del modelo (`premnisa_6.3` §3) | Idem | Pendiente PO |
| 4.3 | Admin: validación global de lo generado y rendimiento del modelo (`premnisa_6.3` §4) | Alineación técnica: [`premnisa_6.3.md`](./premnisa_6.3.md) § “Sobre §4”; US S6.3 | Pendiente PO |

---

## 5. Próximos pasos sugeridos

1. Completar **§4** con el volcado del otro documento.
2. Priorizar **3–5** preguntas de §3 en una sesión PO/BA y pasar respuestas a **`DECISIONES.md`** (S6.3) con fecha.
3. Derivar **US-BE / US-FE** solo después de respuestas (evitar implementar reglas contradictorias).

---

*Creado: 2026-04-12 — plan base abierto para refinement S6.3.*

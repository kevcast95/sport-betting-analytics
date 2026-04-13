# Incremento BT2 > v1 — notas en Sprint 06.1

Sprint **06.1** se **cierra** con la entrega y evidencia en [`EJECUCION.md`](./EJECUCION.md). El **plan técnico completo** del incremento (fases, mix bóveda, ingesta, paridad v1) sigue en **[`../sprint-06.2/incremento_mejora_a_v1_bt2.md`](../sprint-06.2/incremento_mejora_a_v1_bt2.md)** y [`../sprint-06.2/PLAN.md`](../sprint-06.2/PLAN.md).

---

## 5. Preview y detalle de picks — jerarquía antidummies (acuerdo PO/BA, 2026-04-10)

**Principios:** el **diseño actual** (cards, colores, layout) se mantiene; solo se define **orden y jerarquía** de la información. Nombre de producto para el análisis: **Vektor** (sustituye “DSR / razonador” en copy usuario; storytelling completo pendiente).

**Reglas duras**

- **Coherencia:** titular de mercado + **cuota mostrada** + párrafo Vektor deben contar **la misma historia** (no “Victoria Espanyol” con texto y cuota de favorito Barcelona).
- **Sin ruido técnico en UI:** no mostrar al usuario `FT_1X2 · home`, “modelo canónico”, “confianza simbólica”, origen API, completitud CDM, versión pipeline.
- **Confianza:** una línea tipo **“Confianza del modelo: Alta”** anclada al análisis y a la lectura del mercado, sin muletillas de backoffice.
- **Kickoff pasado:** **solo chip** (p. ej. “Partido empezado”); **sin** párrafos largos ni citas D-05/US en superficie; botón Tomar deshabilitado sin muro de texto.
- **Cuota:** **siempre visible** en bloque propio; **nunca** relegada solo a la zona de acciones.
- **Orden fijo:** **evento (A vs B) → competición → (fecha/hora) → mercado + lectura → cuota → chips → Vektor (recortado / completo) → acciones.**

### 5.1 Preview (card) — acotado, contextual

Objetivo: en pocos segundos **quién vs quién**, **qué se sugiere**, **a qué precio**, **atisbo de por qué**.

```
┌─────────────────────────────────────────────────────────┐
│ FC Barcelona  vs  Espanyol                              │  ← 1. PARTIDO (contexto inmediato)
│ La Liga                                                 │  ← competición
│                                                         │
│ Resultado final (1X2)                                   │  ← 2. MERCADO (lenguaje apuesta claro)
│ Victoria local — Barcelona                              │  ← 2b. LECTURA (ejemplo coherente con texto/cuota)
│                                                         │
│ Cuota sugerida  1,31                                    │  ← 3. CUOTA siempre visible (no bajo acciones)
│                                                         │
│ [Estándar]  [Programado]     [Partido empezado]         │  ← chips; aviso de estado = chip, no párrafo
│                                                         │
│ Vektor — por qué                                        │  ← 4. máx. ~2 líneas + …
│ Barcelona en racha (WLWWW), favoritismo marcado en      │
│ el mercado (implícita ~1,31). …                         │
│                                                         │
│ Confianza: Alta                                         │  ← opcional, una línea
│                                                         │
│ [ Detalle ]     [ Tomar pick ]                          │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Detalle — mismo esqueleto, más profundidad

Misma jerarquía que el preview; **Vektor** en párrafo completo; **cuota** en columna de especificación (visible siempre con riesgo/retorno si el flujo lo exige); disclaimer de protocolo solo aquí si aplica, breve o colapsable.

```
┌─────────────────────────────────────────────────────────┐
│ ← Volver a la bóveda                    [ Cómo funciona ]│
│ FC Barcelona vs Espanyol                                │
│ La Bóveda · Revisión · …                                │
├──────────────────────────────┬──────────────────────────┤
│ ESPECIFICACIÓN               │ REGISTRO EN PROTOCOLO    │
│                              │                          │
│ FC Barcelona vs Espanyol     │ (copy corto, 1 línea)    │
│ La Liga                      │                          │
│ Sáb 11 abr 2026 · 11:30      │ [ Tomar pick ]           │
│                              │  (sin citar D-05/US)     │
│ Mercado: Resultado final 1X2 │                          │
│ Lectura: Victoria local      │ [ Volver a la bóveda ]   │
│         (Barcelona)          │                          │
│                              │                          │
│ Cuota sugerida    1,31       │                          │
│ Capital en riesgo …          │                          │
│ Retorno potencial …          │                          │
└──────────────────────────────┴──────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ Vektor — lectura del protocolo                          │
│ (párrafo completo; sin pipeline/CDM/API en superficie)  │
│ Confianza: Alta                                          │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ Sobre el protocolo (1 párrafo; colapsable opcional)      │
└─────────────────────────────────────────────────────────┘
```

### 5.3 Preview vs detalle (qué se acota)

| Elemento | Preview | Detalle |
|----------|---------|---------|
| Partido / liga / hora | Compacto | Completo en especificación |
| Mercado + lectura | Sí, breve | Sí, explícito |
| Cuota | Siempre visible | Siempre visible + riesgo/retorno si aplica |
| Vektor | **~2 líneas máx.** | **Párrafo completo** |
| Disclaimer protocolo | No | Sí (breve / colapsable) |
| Evento ya iniciado | Solo chip + CTA off | Sin caja de advertencia redundante |

**Fallback (regla de producto ya acordada):** si no hay señal suficiente del modelo, mostrar sugerencia alineada a **mayor probabilidad implícita** según cuota en mercado de referencia — obligatorio en copy y en BE.

---

*2026-04-10 — anexo jerarquía ficha; plan completo del incremento en sprint-06.2.*

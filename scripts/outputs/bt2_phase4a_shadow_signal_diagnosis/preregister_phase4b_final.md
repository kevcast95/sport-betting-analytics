# Preregistro final — Fase 4B (diseño congelado, no ejecutado)

**Estado:** documento de diseño experimental. **No** abre 4B ni toca producción.  
**Stack fijo:** shadow, subset5, h2h, `us`, T-60, sin nuevos proveedores ni rediseño de pipeline.  
**Referencia 4A.1:** tiers de N (A &lt; 20, B 20–49, C ≥ 50), bandas de cuota y manifiestos de `selection_side` ya definidos en `summary.json` y en el script de diagnóstico.

---

## 1. Partición holdout (discovery / validation)

### 1.1 Criterio congelado

Partición **por `run_key`**, alineada con la ventana temporal de datos ya persistida:

| Rol | `run_key` incluidos |
|-----|---------------------|
| **Discovery** | `shadow-subset5-backfill-2025-01-05`, `shadow-subset5-recovery-2025-07-12`, `shadow-subset5-backfill-2026-01`, `shadow-subset5-backfill-2026-02`, `shadow-subset5-backfill-2026-03` |
| **Validation** | `shadow-subset5-backfill-2026-04`, `shadow-daily-2026-04-20`, `shadow-daily-2026-04-21`, `shadow-daily-2026-04-22`, `shadow-daily-2026-04-27` |

- **Ningún pick** de validation entra en el conjunto con el que se **etiquetará** a posteriori un segmento como “prometedor” en el paso de descubrimiento; el rol de descubrimiento queda fijado en los cinco runs anteriores.  
- La partición **2026 Q1 (mensuales) → abril 2026 (mensual + dailies)** evita reordenar ad hoc: abril es el primer mes **completo** de cohorte 2026 subset5+CDM mezclado en un solo backfill mensual, **y** añade el bloque `shadow-daily-*` (todo abril), única ventana daily disponible en el baseline.  
- Tamaño aproximado (baseline 297): **~220** picks discovery, **~77** validation. Proporción razonable para comprobar **estabilidad fuera de la franja 2026-01..03** sin vaciar un solo brazo.

### 1.2 Uso

- **Discovery:** descriptivo + identificación de candidatos a segmento, **sujeto a reglas de segmentos y N** (más abajo).  
- **Validation:** comprobar en **holdout fijo** si un segmento univariado que en discovery cumple criterios **vuelve a** cumplirlos; sin redefinir umbrales tras ver validation.

> Si en un futuro entran más `shadow-daily` u otros `run_key`, **no** se incorporan a esta partición 4B sin enmendar este documento con **versión y fecha** (nuevo congelado).

---

## 2. Segmentos permitidos y prohibidos

### 2.1 Univariado (único criterio primario 4B)

Cada análisis “oficial 4B” aplica a **un solo eje a la vez** (una dimensión, un valor o bucket).

| Dimensión | Valores permitidos (cierre 4B) | Notas |
|-----------|-------------------------------|--------|
| **source_path** | `cdm_shadow`, `sportmonks_between_subset5_fallback` | **Excluido** de *promising* primario: `daily_shadow_sm_toa` (muestra insuficiente y estructuralmente distinto; solo lectura anexa, ver CSV). |
| **league_name** | {Premier League, La Liga, Serie A, Ligue 1, Bundesliga} (según `bt2_leagues` en picks) | Misma liga en las dos particiones. |
| **odds_band** | `dec_lt_2`, `dec_2_to_2_5`, `dec_2_5_to_3`, `dec_3_to_4`, `dec_4_to_6`, `dec_ge_6` | **Excluido** de *promising*: `unknown_odds` (scored=0 o sin cuota). |
| **selection_side** | `home`, `away` | **Excluido** de *promising* primario: `unknown`, `unknown_resolved_teams` (N y/o ambigüedad residual 4A.1). `draw` si aparece, solo si *scored* en ambas particiones ≥ 20 (hoy casi inexistente). |
| **time_window** (opcional) | Mismo esquema que 4A (por `run_key`): solo **reporte descriptivo**; **no** combinar con otros ejes. | **No** declarar *promising* “por mes” aislado si el mismo criterio ya se evaluó bajo otra dimensión que lo absorbe. |

### 2.2 Combinaciones cruzadas (2D+)

- **Prohibido** formular criterio de *promising* o regla de selective release sobre **intersecciones** (p. ej. liga × banda) en 4B v1.  
- **Permitido** (opcional) **tabulación de exploración** (anexo) con celdas `scored ≥ 50` **y** anotación “no congelado / no 4B primario”.

Así se evita p-hacking por corte de celdas.

---

## 3. Reglas cuantitativas (4A.1 + 4B)

Tiers de **N sobre `scored`** en **cada** partición por separado:

- **A_inadequate:** scored &lt; 20 → **no interpretar** (salvo conteo de masa).  
- **B_weak_exploratory:** 20 ≤ scored &lt; 50 → **no “promising”**; solo exploratorio.  
- **C_adequate_descriptive:** scored ≥ 50 → descriptivo estable; base para 4B **solo si** se cumple además 3.2.

### 3.1 “No interpretar” (bloqueo duro)

- Cualquier estrato con **A** en discovery **o** validation, para conclusión direccional o rotulación *promising*.  
- `unknown_odds`, `selection_side` en {`unknown`, `unknown_resolved_teams`} para *promising* primario.  
- `daily_shadow_sm_toa` para *promising* primario.  
- Cualquier 2D+ congelado en §2.2.

### 3.2 “Ruido” (no candidato 4B)

- Tier **B** en discovery o en validation, para *promising*.  
- **O** mientras tier C, **cualquiera** de:  
  - `roi_val < roi_disco - 3` (empeoramiento de más de **3 pp** de `roi_flat_stake_pct` en validation frente a discovery, mismos bordes de segmento y definición de ROI que 4A).  
  - Signo opuesto de `roi_flat_stake_units` acumulado en el segmento (discovery vs validation) cuando ambos |ROI unidades| ≥ 1,0 (ruido inestable; evita sobreinterpretar 0,01 unidades).  
- Segmentos cuyo **aporte a ROI** en validation quede dominado por &lt; 3 pick scores (cambio mínimo operativo) — anotar **fragilidad** aun con tier C.

### 3.3 “Prometedor” (candidato, no despliegue; post–4B sigue decidiendo producto)

Se declara un segmento univariado **prometedor (candidato)** solo si **en discovery y en validation** se cumple:

1. **C_adequate_descriptive** (scored ≥ 50) en **ambas** particiones.  
2. `roi_flat_stake_pct` en validation &gt; **-4%** (umbral fijo: leve descenso; coherente con no celebrar P/L malo).  
3. **Estabilidad:** `roi_val ≥ roi_disco - 3` (pp) (no degrada más de 3 pp al pasar a holdout).  
4. Dimensiones: solo las permitidas en §2.1, sin 2D.

*Estos umbrales (-4%, -3 pp) están **congelados** en `phase4b_holdout_plan.json`.*

---

## 4. Ejecución posterior (checklist, sin correr ahora)

1. Calcular medidas por segmento en discovery y en validation (mismo script que 4A.1, partición inyectada).  
2. Aplicar matriz §3.  
3. Listar congelado: {segmento} → (tier disco, tier val, roi_disco, roi_val, veredicto: no interpretar | ruido | prometedor).  
4. Ninguna acción de producto ni API de publicación; solo cierre documental de 4B.

---

## 5. Relación con `preregister_phase4b.md` (4A.1)

Este **preregister_phase4b_final.md** sustituye a la versión preliminar para decisiones; la preliminar queda como histórico de intención. Toda ejecución 4B se rige **solo** por este final + `phase4b_holdout_plan.json` + `phase4b_allowed_segments.csv`.

---

*Documento congelado para paso puente 4A → 4B. Revisión solo con versión + fecha + razón de cambio.*

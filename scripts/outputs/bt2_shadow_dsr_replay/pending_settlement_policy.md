# BT2 Shadow DSR — política de cierre de resultados

Alcance: solo carril `shadow` (`bt2_shadow_*`), sin tocar producción.

## Objetivo

Separar claramente:
- cierre oficial
- resultado visible pero no oficial
- pending para recheck
- cierre manual auditado

## Estados operativos propuestos

| Estado operativo | Regla DB (shadow) | Qué significa |
|---|---|---|
| `cierre_oficial` | `bt2_shadow_pick_eval.eval_status IN ('hit','miss','void','no_evaluable')` | El pick ya tiene veredicto oficial dentro del carril shadow. |
| `resultado_visible_no_oficial` | `eval_status='pending_result'` **y** hay marcador visible (`result_home` + `result_away`) | Hay score, pero todavía no hay cierre oficial confiable del evaluador. |
| `pending_recheck` | `eval_status='pending_result'` y sin score final | Falta verdad final o refresh CDM/SM para resolver. |
| `cierre_manual_auditado` | `eval_notes` con marca manual (`manual`) | Cierre excepcional, auditado, sin sobreescribir la verdad oficial base. |

## Cuándo mantener `pending` aunque haya score visible

Mantener `pending_result` cuando:
- el score visible no cumple criterio de cierre oficial (p.ej. estado de evento inestable o no finalizado de forma confiable),
- hay discrepancia de fuente/consistencia y se requiere una corrida de recheck,
- o el flujo de evaluación oficial aún no confirmó el cierre.

## Cuándo corresponde solo recheck

`pending_recheck` aplica cuando:
- no hay score final en CDM para el pick,
- o hay score parcial/sin condiciones de cierre oficial.

Acción: reintento de refresh/evaluación en shadow, sin cierres manuales por defecto.

## Cuándo proponer cierre manual auditado

Solo como excepción:
- existe evidencia externa suficiente y trazable,
- el pending persiste tras rechecks razonables,
- y se documenta causa en `eval_notes`.

No reemplaza la verdad oficial: es una marca auditada para operación/monitoreo.

## Contrato DB/UI mínimo (sin migraciones)

- DB:
  - Se reutiliza `bt2_shadow_pick_eval.eval_status`.
  - Se reutiliza `bt2_shadow_pick_eval.eval_notes` para marca manual auditada.
- UI/Admin:
  - Se expone `settlementStage` derivado (sin escribir estado nuevo):
    - `cierre_oficial`
    - `resultado_visible_no_oficial`
    - `pending_recheck`
    - `cierre_manual_auditado`

## Qué no cambia

- No se toca producción.
- No se altera el truth source oficial.
- No se cambian reglas de T-60/mercado/región/subset5.

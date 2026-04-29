# BT2 Shadow DSR — contrato de visibilidad por pick (UI/Admin)

Objetivo: hacer visible el comportamiento real del carril DSR en la UI/admin existente de shadow.

## Campos expuestos por fila (`monitor-resultados-shadow`)

- Identidad de corrida:
  - `runKey`
  - `selectionSource`
- Metadata DSR:
  - `dsrModel`
  - `dsrPromptVersion`
  - `dsrParseStatus`
  - `dsrFailureReason`
  - `dsrNoPickReason`
  - `dsrMarketCanonical`
  - `dsrSelectionCanonical`
  - `dsrSelectedTeam`
  - `dsrResponseExcerpt`
  - `dsrConfidenceLabel`
- Estado de evaluación/cierre:
  - `evaluationStatus`
  - `evaluationReason`
  - `resultScoreText`
  - `settlementStage`

## Mapeo de clasificación visual sugerido

- **Pick válido**: `dsrParseStatus='ok'`
- **Abstención**: `dsrParseStatus='dsr_empty_signal'` (usar `dsrNoPickReason`)
- **Fallo técnico**: `dsrParseStatus='dsr_failed'` (usar `dsrFailureReason`)
- **Pending**: `settlementStage='pending_recheck'`
- **Settled**: `settlementStage='cierre_oficial'`

## Notas operativas

- El endpoint no crea UI nueva; amplía la carga del monitor shadow existente.
- Si no hay campos crudos en `dsr_raw_summary_json`, el valor puede venir `null`.
- `settlementStage` es derivado en backend para visualización; no introduce nuevo estado persistido.

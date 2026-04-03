# BetTracker 2.0 — Carpeta de Ejecucion

Esta carpeta centraliza la ejecucion de la nueva etapa (API-first + CDM + reglas conductuales).

## Regla operativa

- La fuente de verdad para ejecucion es `US.md` de cada sprint.
- Las US usan **prefijos por capa**: `US-BE-###` (backend), `US-FE-###` (frontend), `US-DX-###` (contratos), `US-OPS-###` (operacion). Detalle en `01_CONTRATO_US.md`.
- Si hay contradiccion entre conversaciones y archivos, manda lo documentado en esta carpeta.
- No se mezclan tareas de producto legacy con tareas BT2 en el mismo archivo.

## Estructura

- `00_IDENTIDAD_PROYECTO.md`: identidad estable del proyecto (para recuperar contexto).
- `04_IDENTIDAD_VISUAL_UI.md`: norte visual (Zurich Calm) para UI sobria y anti-urgencia.
- `01_CONTRATO_US.md`: contrato estricto para redactar Historias de Usuario.
- `02_PLAYBOOK_HIBRIDO.md`: como trabajar Gemini (diseño) + Cursor (ejecucion).
- `03_RUTAS_PARALELAS_V1_V2.md`: estrategia para correr en paralelo sin apagar el sistema actual.
- `sprints/`: trabajo secuencial por sprint.

## Flujo recomendado

1. Crear/actualizar `sprints/sprint-XX/US.md`.
2. Derivar tareas en `TASKS.md`.
3. Ejecutar y registrar decisiones en `DECISIONES.md`.
4. Cerrar con checklist en `QA_CHECKLIST.md`.

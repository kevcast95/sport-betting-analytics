# Playbook Hibrido (Gemini + Cursor)

## Objetivo

Maximizar calidad de diseno y velocidad de implementacion sin quemar cuota.

## Distribucion de roles

- Gemini: arquitectura abstracta, trade-offs, propuestas de CDM, roadmap.
- Cursor: viabilidad en codebase real, implementacion, refactor, pruebas, commit.

## Ciclo recomendado (cerrado)

1. Diseno fuera (Gemini): US + contrato JSON + decisiones.
2. Validacion aqui (Cursor): gap analysis y plan tecnico.
3. Ejecucion aqui: cambios de codigo + verificacion.
4. Auditoria fuera: revisar decisiones y metricas.
5. Cierre: actualizar archivos del sprint.

## Plantilla minima para pedir ejecucion a Cursor

```md
Sprint: sprint-XX
US: US-BE-001 / US-FE-001 / ...
Objetivo:
Alcance:
Archivos/capas esperadas:
Contrato JSON:
Reglas no negociables:
DoD:
```

Las US van documentadas en `sprints/sprint-XX/US.md` con prefijos por capa (ver `01_CONTRATO_US.md`).

## Regla de oro

No mezclar exploracion extensa y codificacion en el mismo turno.

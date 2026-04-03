# Contrato para Historias de Usuario (US)

Este archivo define como redactar US para que Cursor pueda ejecutar sin ambiguedad.

## Convencion de identificadores (obligatoria)

Cada US lleva **prefijo de capa** + numero secuencial **por capa** dentro del sprint (reinicia BE-001, FE-001, etc.).

| Prefijo | Capa | Ejemplos |
|--------|------|----------|
| `US-BE-###` | Backend: API FastAPI, jobs, SQLite, ACL, adaptadores | `US-BE-001` |
| `US-FE-###` | Frontend: React, estado, rutas V2, copy UX | `US-FE-001` |
| `US-DX-###` | Contratos compartidos: OpenAPI, tipos TS, esquemas JSON | `US-DX-001` |
| `US-OPS-###` | Operacion: env, deploy, observabilidad, runbooks | `US-OPS-001` |

### Organizacion en `US.md`

Un solo archivo `sprints/sprint-XX/US.md` con **secciones**:

```md
## Backend
### US-BE-001 - ...
## Frontend
### US-FE-001 - ...
## Contratos
### US-DX-001 - ...
## Operacion
### US-OPS-001 - ...
```

En `TASKS.md`, cada tarea referencia la US: `- [ ] T-005 (US-FE-002) ...`

### Referencias visuales (HTML en `refs/`)

Archivos en `sprints/sprint-XX/refs/` con nombre ejecutable:

`us_<capa>_<id>_<slug>.md` (minúsculas, slug descriptivo). Ejemplos: `us_fe_001_login.md`, `us_fe_002_bankroll.md`.

Cada US que use mock HTML debe **enlazar** el archivo en **Contexto técnico** o **Alcance**. La implementación en React no debe copiar CDNs de la ref (Tailwind CDN, fuentes de iconos de terceros) si el contrato de producto lo prohíbe; se portan tokens y layout.

## Formato obligatorio por US

```md
## US-BE-001 - <titulo corto>

### 1) Objetivo de negocio
<resultado esperado en 1-2 frases>

### 2) Alcance
- Incluye:
  - ...
- Excluye:
  - ...

### 3) Contexto tecnico actual
- Modulos afectados:
  - `ruta/archivo_a`
  - `ruta/archivo_b`
- Dependencias externas:
  - ...

### 4) Contrato de entrada/salida (si aplica)
```json
{
  "input": {},
  "output": {}
}
```

### 5) Reglas de dominio
- Regla 1:
- Regla 2:

### 6) Criterios de aceptacion (Given/When/Then)
1. Given ...
   When ...
   Then ...

### 7) No-funcionales
- Performance:
- Observabilidad:
- Seguridad:
- Compatibilidad:

### 8) Riesgos y mitigacion
- Riesgo:
  - Mitigacion:

### 9) Plan de pruebas
- Unitarias:
- Integracion:
- Manual UI:

### 10) Definition of Done
- [ ] Codigo implementado
- [ ] Tipado estricto
- [ ] Tests verdes
- [ ] Documentacion actualizada
- [ ] Sin acoplamiento a proveedor en UI/IA
```

## Reglas de calidad de una US

- Debe usar el prefijo correcto (`US-BE-`, `US-FE-`, `US-DX-`, `US-OPS-`).
- Debe ser implementable en <= 2 dias de trabajo real.
- Debe nombrar rutas/capas impactadas.
- Debe declarar explicitamente si toca V1, V2 o ambas.
- Debe incluir criterio de rollback.

## Semaforo de implementacion

- Verde: sin decisiones abiertas, ejecutar.
- Amarillo: 1-2 decisiones abiertas, resolver antes de codificar.
- Rojo: contrato incompleto o ambiguo, no ejecutar.

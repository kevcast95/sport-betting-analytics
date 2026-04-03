# Sprint 01 - US (Fuente de verdad)

> Este archivo define que se implementa en Sprint 01.
> Todo cambio tecnico debe mapear a una US aqui.

## Estado del sprint

- Fecha inicio:
- Fecha fin:
- Owner:
- Estado: Planned / In Progress / Done

## US incluidas

Prefijos obligatorios por capa: `US-BE-###`, `US-FE-###`, `US-DX-###`, `US-OPS-###` (ver `../../01_CONTRATO_US.md`).

## Backend

### US-BE-001 - [PENDIENTE]

## Frontend

### US-FE-001 - Autenticación y Protocolo de Acceso (Búnker Gate)
1) Objetivo de negocio
Establecer la puerta de entrada segura a BetTracker 2.0, garantizando que el usuario acepte el Contrato de Disciplina antes de visualizar cualquier métrica financiera o deportiva.

2) Alcance
Incluye:

Pantalla de Auth unificada (V2) con toggle entre Login/Signup.

Modal de "Contract of Discipline" con 3 checkboxes obligatorios para acceso al Dashboard.

Layout base (BunkerLayout) con Sidebar y Header funcional.

Excluye:

Persistencia en base de datos real (se usará Mock Auth en este sprint).

3) Contexto tecnico actual
Modulos afectados:

src/pages/AuthPage.tsx

src/layouts/BunkerLayout.tsx

src/store/useUserStore.ts

Dependencias externas:

framer-motion, lucide-react, zustand.

4) Contrato de entrada/salida
JSON
{
  "input": {
    "authMode": "LOGIN | SIGNUP",
    "credentials": { "email": "string", "password": "password" }
  },
  "output": {
    "authStatus": "SUCCESS | FAILED",
    "userState": {
      "isAuthenticated": true,
      "hasAcceptedContract": false,
      "operatorName": "string"
    }
  }
}
5) Reglas de dominio
Regla 1: El acceso a /dashboard está prohibido si hasAcceptedContract es false.

Regla 2: El botón "Commit to the Protocol" requiere que los 3 checks de axiomas sean true.

Regla 3: V2 únicamente. No afecta rutas ni componentes de la V1.

6) Criterios de aceptacion
Given un usuario no logueado, When intenta entrar a la app, Then debe ver el formulario de Auth con estética Zurich Calm.

Given un login exitoso, When hasAcceptedContract es falso, Then debe aparecer el modal del contrato bloqueando el resto de la UI.

7) No-funcionales
Performance: Transiciones de Auth < 300ms.

Observabilidad: Log en consola de intentos de bypass del contrato.

Seguridad: Persistencia de flags de contrato en localStorage con cifrado básico.

Compatibilidad: Renderizado responsivo para Desktop (1440px) y Laptop (1024px).

8) Riesgos y mitigacion
Riesgo: El usuario puede intentar forzar la URL del dashboard.

Mitigacion: Middleware de ruta que verifica el estado de hasAcceptedContract en Zustand.

Criterio de Rollback: Revertir a commit inicial de BunkerLayout si el estado global se corrompe en el refresh.

9) Plan de pruebas
Unitarias: Verificar el toggle del estado de Auth entre Login y Signup.

Integracion: Validar que el cambio en useUserStore dispare la apertura/cierre del modal del contrato.

Manual UI: Confirmar el uso de Geist Mono en campos de contraseña y tokens.

10) Definition of Done
[ ] Codigo implementado

[ ] Tipado estricto

[ ] Tests verdes

[ ] Documentacion actualizada en docs/bettracker2/

[ ] Sin acoplamiento a proveedor en UI/IA

## Contratos

### US-DX-001 - [PENDIENTE]

## Operacion

### US-OPS-001 - [PENDIENTE]

# Rutas paralelas (V1 y V2 en paralelo)

Objetivo: ejecutar upgrade sin apagar el sistema actual.

## Estrategia recomendada

- Mantener experiencia actual bajo rutas legacy (V1).
- Exponer funcionalidades nuevas bajo namespace V2.
- Controlar acceso con feature flags por modulo.

## Propuesta de rutas UI

- V1 (actual):
  - `/`
  - `/runs`
  - `/runs/:dailyRunId/events`
  - `/runs/:dailyRunId/picks`
- V2 (nuevo dominio conductual):
  - `/v2`
  - `/v2/session` (auth + modal de contrato)
  - `/v2/dashboard` (Búnker tras sesión mock y contrato firmado)
  - `/v2/settings` (configuración V2; acceso al Treasury Modal)
  - `/v2/risk`
  - `/v2/protocol`
  - `/v2/reports`

## Propuesta de rutas API

- V1:
  - `/dashboard`
  - `/daily-runs/*`
  - `/picks/*`
- V2:
  - `/api/v2/events/*`
  - `/api/v2/markets/*`
  - `/api/v2/behavior/*`
  - `/api/v2/risk/*`

## Regla anti-acoplamiento

- Los payloads V2 no deben contener nombres de proveedor (`sportmonks`, `the_odds`, etc.).
- Todo pasa por entidades canonicas.

## Criterio de corte

Se puede retirar V1 solo cuando:
- cobertura de datos V2 >= objetivo pactado,
- KPIs de estabilidad y calidad en verde durante al menos 2 semanas,
- checklist de paridad funcional completado.

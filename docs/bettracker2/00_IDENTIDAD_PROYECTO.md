# Identidad del Proyecto (BetTracker 2.0)

## Vision

BetTracker 2.0 es un protocolo de gestion conductual y riesgo deportivo.
El objetivo principal no es "mostrar picks", sino proteger bankroll y comportamiento del usuario.

## Principios no negociables

1. API-first (deprecando scraping como base principal).
2. Anti-Corruption Layer obligatoria.
3. Frontend y motor de IA agnosticos a proveedor.
4. Migracion incremental (sin apagar V1).
5. Trazabilidad: toda regla debe ser auditable por metrica.
6. Traduccion humana de datos (UX copywriting): la UI no puede mostrar metricas frias sin contexto. Todo porcentaje/indicador tecnico debe incluir lectura amigable y accionable en terminos de bolsillo y comportamiento.
7. Todo el contenido debe ser en español hasta que implementemos apis para translates.

## Arquitectura objetivo (alto nivel)

- Proveedores externos (The-Odds-API, Sportmonks, otros).
- Capa de adaptadores por proveedor.
- Capa canonica (CDM): Event, Participant, Market, OddsSnapshot, Result, BehavioralState.
- Servicios de dominio (riesgo, elegibilidad, bloqueo conductual).
- API interna estable para UI e IA.

## Reglas de continuidad

- V1 (actual) debe seguir operativa durante la migracion.
- V2 se despliega por rutas separadas y feature flags.
- Ningun componente V2 puede importar DTOs crudos de proveedor.

## Metricas base de migracion (separadas por audiencia)

### A) Metricas de ingenieria (admin/backend)

- Cobertura de odds por deporte/mercado.
- % de eventos analizables vs % descartados por falta de datos.
- Latencia end-to-end de la capa anti-corrupcion.
- Tasa de errores de identity mapping (cruces fallidos entre proveedores).

### B) Metricas de salud financiera y conductual (usuario/UI)

El backend debe exponer estructura para que la UI traduzca cada metrica a lenguaje humano:

- ROI:
  - tecnico: `roi_pct`
  - copy UI: "Crecimiento sostenible: por cada 100 COP invertidos, el sistema genera X COP de ganancia limpia."
- Drawdown:
  - tecnico: `max_drawdown_units`
  - copy UI: "Control de danos: tu peor racha costo X unidades, pero el capital principal sigue protegido."
- Bloqueo conductual:
  - tecnico: `behavioral_block_count` y `estimated_loss_avoided_cop`
  - copy UI: "Intervenciones de proteccion: el sistema pauso X impulsos y evito una perdida estimada de Y COP."
- Hit rate:
  - tecnico: `hit_rate_pct`
  - copy UI: "Constancia: aciertas X de cada 10 analisis; tu disciplina habilita mejores recomendaciones."

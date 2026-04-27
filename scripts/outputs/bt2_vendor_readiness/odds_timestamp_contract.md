# Contrato de timestamps — odds (BT2 + The Odds API laboratorio)

## Campos y significado

| Campo | Definición |
|-------|------------|
| `provider_snapshot_time` | Instantánea del proveedor de odds (TOA: timestamp devuelto en histórico; cercano a granularidad 5 min según doc TOA). |
| `provider_last_update` | Última actualización declarada por el book dentro del payload TOA (`last_update` en mercado/bookmaker). |
| `ingested_at` | Momento en que nuestro sistema persistió la fila (wall clock ingest). **No es tiempo de mercado.** |
| `backfilled_at` | Momento de backfill/reproceso si aplica. **No es tiempo de mercado.** |
| `kickoff_utc` | Inicio del evento (fixture master SM / `bt2_events`). |
| `T-60_cutoff` | `kickoff_utc - 60 minutos` — ventana usada en modo `historical_sm_lbu` (3C) para líneas SM; análogo conceptual para TOA en laboratorio. |

## Regla explícita (obligatoria)

- **Nunca** usar `ingested_at` ni `backfilled_at` como si fueran el tiempo real del mercado o de la cuota.
- Para análisis ex-ante, la verdad temporal debe ser `provider_snapshot_time` / `provider_last_update` (según contrato del endpoint TOA) alineada a `T-60_cutoff` o política explícita del experimento.

## Bounded replay actual

- No modificado en esta fase. Mantener separado de este contrato de laboratorio TOA.

## Referencia de coste TOA (histórico)

- Documentación TOA v4: odds históricas por deporte/snapshot — coste **10 créditos × regiones × mercados** por llamada al endpoint bulk histórico; evento histórico puntual — coste basado en `10 × mercados_únicos × regiones` por request de odds de evento.

# Contrato de persistencia — laboratorio piloto The Odds API (no productivo)

Definición de campos para cuando se persistan resultados del piloto (tabla laboratorio o CSV). **No implementa pipeline productivo.**

## Timestamps

| Campo | Significado |
|-------|-------------|
| `provider_snapshot_time` | Instantánea declarada por el proveedor TOA en la respuesta (tiempo de mercado/snapshot del payload histórico). |
| `provider_last_update` | Última actualización del book dentro del mercado/outcome TOA (`last_update` por bookmaker/outcome cuando aplique). |
| `ingested_at` | Cuando nuestro proceso escribió la fila en almacenamiento local. **No es tiempo de mercado.** |
| `backfilled_at` | Si un job reprocesó o backfiltró la fila. **No es tiempo de mercado.** |
| `kickoff_utc` | Inicio del partido (`bt2_events.kickoff_utc` / fixture master SportMonks). |

**Regla:** nunca usar `ingested_at` ni `backfilled_at` como sustituto del tiempo real del mercado o de la cuota.

## Identificación mercado / evento

| Campo | Significado |
|-------|-------------|
| `sport_key` | Clave TOA del deporte/liga (`the_odds_api_sport_key_expected`). |
| `market` | Mercado TOA (`h2h` para piloto FT_1X2). |
| `region` | Región de bookmakers (`us` en piloto inicial). |
| `bookmaker` | Identificador/nombre bookmaker en respuesta TOA. |
| `outcome_name` | Etiqueta outcome (ej. equipo / Draw) tal cual TOA. |
| `decimal_price` | Probabilidad implícita como decimal desde outcome TOA (normalizado para análisis). |

## Matching y estado laboratorio

| Campo | Significado |
|-------|-------------|
| `sm_fixture_id` | ID fixture SportMonks (referencia BT2). |
| `bt2_event_id` | ID interno BT2. |
| `the_odds_api_event_id` | ID evento devuelto por TOA tras paso A. |
| `fixture_matching_status` | Ver `pilot_result_taxonomy.md` (matched / unmatched / gap). |
| `laboratory_classification_status` | Clasificación del resultado del experimento (taxonomía piloto). |

--- 

*Piloto subset 5, mercado único h2h, región us, snapshots T-60.*

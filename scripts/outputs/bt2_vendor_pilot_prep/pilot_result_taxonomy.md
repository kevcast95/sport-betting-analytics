# Taxonomía de resultados — laboratorio piloto The Odds API

Estados mínimos para clasificar cada intento cuando existan llamadas reales.

| Estado | Cuándo usar |
|--------|-------------|
| `matched_with_odds_t60` | Evento TOA matcheado y respuesta odds h2h en snapshot T-60 con outcomes utilizables. |
| `matched_without_odds_t60` | Evento matcheado pero sin mercado h2h o sin precios en ventana T-60. |
| `unmatched_event` | No se encontró evento TOA coherente con SM/BT2 para el sport_key y fecha/snapshot. |
| `league_not_supported` | `sport_key` o liga no disponible en TOA para el piloto. |
| `market_not_supported` | Deporte/liga ok pero mercado `h2h` no devuelto o vacío. |
| `bookmaker_gap` | Mercado existe pero ningún bookmaker en región `us` (o lista vacía). |
| `timestamp_gap` | Odds existen pero `provider_snapshot_time` / alineación T-60 es inválida o fuera de ventana. |
| `normalization_gap` | No se pudo mapear outcome a lado BT2 / decimal / nombre equipo tras normalizar. |

Los campos `fixture_matching_status` y `laboratory_classification_status` en persistencia deben referenciar estos valores o refinamientos documentados en el mismo experimento.

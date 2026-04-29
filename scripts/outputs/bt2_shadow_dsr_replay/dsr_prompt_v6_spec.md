# DSR shadow-native — prompt v6 (analista + JSON estricto)

## Objetivo

Recuperar **identidad de selector**, **criterio ex-ante defendible** y **campos auditables** (`confidence_label`, `rationale_short_es`) sin abandonar **salida JSON única** (`response_format: json_object`) y **schema fijo por evento**.

## Dónde vive el código (desacoplado del cliente compartido)

| Pieza | Archivo |
|-------|---------|
| Versión y prompts (system estable + user modular FT_1X2) | `apps/api/bt2_dsr_shadow_native_prompt_v6.py` |
| HTTP DeepSeek + parser sólo v6 | `apps/api/bt2_dsr_shadow_native_deepseek_v6.py` |
| Carril replay native que **usa v6 explícitamente** | `scripts/bt2_shadow_dsr_full_replay_native.py` → `deepseek_suggest_batch_shadow_native_v6_with_trace` |
| Prueba controlada muestra 32 (sin insert masivo) | `scripts/bt2_shadow_dsr_prompt_v6_controlled.py` |

**No se modifica** `apps/api/bt2_dsr_deepseek.py` (contrato batch compartido / producción ajena al experimento).

Metadato persistido en replay native: `dsr_prompt_version = shadow_native_dsr_prompt_v6` (distinto de `CONTRACT_VERSION_PUBLIC`).

## System prompt (resumen)

- Rol: selector pre-partido BT2 en carril shadow-native.
- Fuentes permitidas: `consensus`, `diagnostics` (incl. `prob_coherence`), `event_context`, y **sólo** bloques `processed.*` con `available=true` cuando apliquen; lo disponible pesa más que ausencias.
- `prob_coherence`: señal diagnóstica, **no** veto automático.
- Prohibido: inventar cuotas/lesiones/rachas/edge; citar bloques no presentes; texto fuera del JSON.
- Decisión: no elegir por defecto al favorito cuota-baja ni por payout; abstención (`UNKNOWN`) sólo para datos críticos faltantes o contradicción severa, no por incertidumbre normal.

## User prompt modular (resumen)

- Invariantes por corrida: `primary_market_for_this_run`, `allowed_markets`, `allowed_selections_by_market`, schema **exacto** de siete claves por evento.
- Bloque sustituible **Mercado activo** (ahora FT_1X2); otros mercados en el futuro cambian sólo este bloque + listas allowlist en el mismo user prompt.

## Schema de salida (por evento)

Claves **exactas** (sin extras):

- `event_id` (int)
- `market_canonical`: `FT_1X2` \| `UNKNOWN`
- `selection_canonical`: `home` \| `draw` \| `away` \| `unknown_side`
- `selected_team` (string; vacío si draw o UNKNOWN)
- `confidence_label`: `high` \| `medium` \| `low`
- `rationale_short_es` (frase corta ES basada en el input; vacío si UNKNOWN sin pick)
- `no_pick_reason` (vacío si hay pick; obligatorio si UNKNOWN)

Parseo: `apps/api/bt2_dsr_shadow_native_deepseek_v6.py` descarta claves extra del modelo con log y construye narrativa interna para `postprocess_dsr_pick` + etiquetas existentes.

## Cambio respecto a la política “v5” embebida en `bt2_dsr_deepseek`

La política de abstención mínima seguía en el **system compartido** orientado a compactar fallos de parseo; v6 **no altera ese archivo**: mueve reglas de analista + rationale + confianza al **módulo shadow-only**, manteniendo `json_object` y envelope `ds_input` validado igual que antes.

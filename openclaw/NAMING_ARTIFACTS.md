# Convención de nombres — `out/` (candidatos y ventanas)

Evita ruido y archivos genéricos (`candidates.json`, `morning` sin fecha). Todo bajo **`out/`** con **fecha** y **fase de ejecución** explícitas.

## Regla

| Archivo | Cuándo | ¿Una o dos veces al día? |
|---------|--------|---------------------------|
| **`out/candidates_{DATE}_select.json`** | Salida de `select_candidates` tras el ingest del día `{DATE}` | **Una vez** por `daily_run` / día calendario CO. |
| **`out/candidates_{DATE}_exec_08h.json`** | Salida de `event_splitter` `--slot morning` | Una vez por ventana mañana (lee el `_select` de ese `{DATE}`). |
| **`out/candidates_{DATE}_exec_16h.json`** | Salida de `event_splitter` `--slot afternoon` | Una vez por ventana tarde (mismo `_select` de ese `{DATE}`). |

`{DATE}` = `YYYY-MM-DD` (día del run en `America/Bogota`, alineado al ingest de medianoche).

**Las dos analíticas (08:00 y 16:00) comparten el mismo `candidates_{DATE}_select.json`**; no regeneran select salvo que re-ejecutes el job a propósito. Cada ventana solo genera su `exec_08h` o `exec_16h`.

## Lotes (tokens)

Prefijo recomendado para `split_ds_batches`:

```text
out/batches/candidates_{DATE}_exec_08h
out/batches/candidates_{DATE}_exec_16h
```

→ archivos `..._batch01of05.json`, etc.

## Parciales Telegram (merge)

```text
out/payload_{DATE}_exec_08h_part01.json
```

(o el patrón que uses; lo importante es incluir `{DATE}` y `exec_08h` / `exec_16h`.)

## Legacy

- `candidates.json` en la raíz del repo: solo scripts viejos / E2E manual; **no** usar en cron ni OC.

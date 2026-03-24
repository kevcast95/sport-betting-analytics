# Optimización: timeout, coste y tokens (cron 08:00 / 16:00)

## Qué pasó (resumen)

- Mandar **todo** `ds_input` de una ventana (p. ej. 18 eventos con `processed` completo) en **una sola** llamada al modelo → **50k–80k+ tokens de entrada** + salida larga → **>10 min** con `deepseek-reasoner` → **timeout** del agente (~600 s).
- Cada reintento o job largo **multiplica el coste**; en pocas horas se puede quemar presupuesto si el razonador procesa lotes enormes varias veces.
- **`candidates.json` sin fecha** facilita datos **viejos**; usar **`out/candidates_${DATE}_select.json`** + **`exec_08h` / `exec_16h`** (ver `NAMING_ARTIFACTS.md`).

---

## Acciones recomendadas (orden)

### 1) Subir timeout (parche rápido, no sustituye lotes)

En OpenClaw / config del agente, sube `agents.defaults.timeoutSeconds` (ej. **1200–1800** si insistes en **un solo** megaprompt). Sigue siendo frágil si crece el calendario.

### 2) No usar `deepseek-reasoner` en cron de volumen

Para **08:00 y 16:00** programados, usa un modelo **más rápido y barato** (`deepseek-chat`, flash, etc.). Reserva el **reasoner** para revisiones puntuales o lotes de ≤3 eventos.

### 3) Lotes con `split_ds_batches.py` (recomendado en repo)

Después de `event_splitter`:

```bash
python3 jobs/split_ds_batches.py \
  -i out/candidates_${DATE}_exec_08h.json \
  -o out/batches/candidates_${DATE}_exec_08h \
  --chunk-size 4 \
  --slim
```

- **`--slim`**: quita `run_inventory` y basura; solo metadatos útiles + `ds_input` del lote → **menos tokens**.
- **`--chunk-size 4`** (o 3): varias llamadas secuenciales cortas, cada una bajo el timeout.

Flujo OC:

1. Para cada `*_batchNNofMM.json`, ejecutar el analista → guardar `out/payload_morning_batch01.json` (mismo esquema `telegram_payload` pero solo `events` de ese lote).
2. Al terminar todos los lotes de esa ventana:

```bash
python3 jobs/merge_telegram_payload_parts.py \
  -i out/payload_morning_batch*.json \
  -o out/telegram_payload.json
```

3. `render_telegram_payload.py` → Telegram (un mensaje por ventana, como antes).

### 4) Limitar candidatos en select (operativo)

Si no necesitas 18+ picks por ventana:

```bash
python3 jobs/select_candidates.py ... --limit 10 -o "out/candidates_${DATE}_select.json"
```

### 5) Rutas con fecha

Patrón: `out/candidates_${DATE}_select.json` (compartido 08h y 16h), `out/candidates_${DATE}_exec_08h.json`, `exec_16h`, lotes bajo `out/batches/`. Ver `NAMING_ARTIFACTS.md`.

---

## Coste “4 USD en 7 h”

Es coherente si:

- Varios jobs largos con **reasoner** + **60k+ tokens** de entrada cada uno, o
- Reintentos tras timeout, o
- Análisis manual + cron solapados.

Los lotes **`--slim` + chunk 3–4** suelen bajar entrada **por llamada** un orden de magnitud respecto a “18 eventos + inventario completo”.

---

## Checklist pre–cron

- [ ] `DATE` y `daily_run_id` del día correcto  
- [ ] `event_splitter` → archivo de ventana del día  
- [ ] `split_ds_batches` con `--slim`  
- [ ] Modelo cron ≠ reasoner (salvo excepción)  
- [ ] `timeoutSeconds` acorde al peor lote (ej. 8–12 min **por lote**, no por los 18 juntos)

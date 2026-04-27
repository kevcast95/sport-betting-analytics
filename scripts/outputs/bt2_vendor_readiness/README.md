# BT2 — Vendor readiness (Fase 3D)

## Regenerar (datos reales)

Con `BT2_DATABASE_URL` válido y **sin** `BT2_VENDOR_READINESS_OFFLINE`:

```bash
cd /Users/kevcast/Projects/scrapper
python3 scripts/bt2_vendor_readiness_phase3d.py
```

## Modo offline / CI

Si no hay base de datos (o forzar stubs):

```bash
BT2_VENDOR_READINESS_OFFLINE=1 python3 scripts/bt2_vendor_readiness_phase3d.py
```

Los CSV de auditoría SM, mapping por cohorte A, muestra y créditos quedarán vacíos o stub; `readiness_summary.json` marcará `no_listos`.

## Salidas

Ver lista en `scripts/bt2_vendor_readiness_phase3d.py` (comentario final) o en el README generado tras ejecución con DB.

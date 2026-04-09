# Sprint 06.1 — Ejecución y evidencia de cierre

> **Uso:** rellenar durante el sprint. **Check cierre:** [`TASKS.md`](./TASKS.md) § *Check cierre Sprint 06.1*.  
> **Escenarios obligatorios:** **US-BE-036** (tres casos) + **D-06-022** / **D-06-026** §6.

## Estado

| Campo | Valor |
|--------|--------|
| Rama / PR principal | Completar al abrir el sprint |
| Última actualización | Completar en cada cierre parcial |

## Escenarios US-BE-036 (evidencia)

Para cada fila: método de prueba (test automatizado, manual, fixture) y enlace a PR o commit.

| # | Escenario | Resultado | Evidencia (PR, test, nota) |
|---|-----------|-----------|----------------------------|
| 1 | Post-DSR produce picks DSR → persisten con fuente/lineage coherente | ☐ OK / ☐ N/A | |
| 2 | DSR vacío + CDM con candidatos SQL válidos → fallback + mensaje/disclaimer + lineage | ☐ OK | |
| 3 | Vacío duro (**D-06-026** §6: **0** filas pool elegible) → **cero** picks, API/mensaje operativo claro | ☐ OK | |

## Post-DSR (T-181–T-182)

- Casos borde ejecutados (cuota desvío > ±15%, mercado inválido → omitir, odds modelo > 15 cap confianza): indicar **sí/no** y ubicación (archivo de test o sección manual).

## Contrato / FE

- Campos nuevos vault/admin alineados **T-173** + **T-184**: lista breve o enlace al diff del PR.

## Notas

*(Decisiones tomadas en implementación que no cambian DECISIONES — si cambian contrato, actualizar **DECISIONES.md** antes de merge, **D-06-023**.)*

---

*Plantilla: 2026-04-09 — S6.1 apto ejecución.*

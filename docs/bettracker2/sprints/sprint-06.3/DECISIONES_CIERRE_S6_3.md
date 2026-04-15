# Sprint 06.3 — DECISIONES_CIERRE

> Jerarquía: norte y fases en `ROADMAP_PO_NORTE_Y_FASES.md`; backlog maestro del sprint en `PLAN.md`.
> Base vigente del sprint: `DECISIONES.md`, `US.md`, `TASKS.md`, `EJECUCION.md`.
> Documento base de este cierre: `CIERRE_RESTANTE_S6_3.md`.
> Base aprobada previa: `CIERRE_FASE_0_MODELO_Y_METRICA_DATOS.md`.
> Convención alcance: D-06-023 (cambio en código → nueva US / decisión antes de merge).

* * *

## D-06-051 — El slice principal de Fase 1 no se considera cerrado sin evidencia operativa real (2026-04-14)

Contexto: S6.3 ya implementó el slice técnico principal de Fase 1, pero no basta con tener tabla/modelo, job, endpoint, vista, tests y build satisfactorios si no existe evidencia real del loop con picks existentes en entorno operativo.

Decisión:
  1. S6.3 no podrá declararse cerrado solo con implementación técnica del slice principal de Fase 1.
  2. Para cerrar realmente este frente deberá existir evidencia operativa real de que picks existentes en `bt2_daily_picks` generan fila en `bt2_pick_official_evaluation`.
  3. La evidencia mínima aceptable deberá mostrar, para un subconjunto real identificado por `operating_day_key`:
     * picks reales procesados,
     * filas reales en `bt2_pick_official_evaluation`,
     * al menos estado `pending_result` y, cuando aplique, estados evaluados reales,
     * y evidencia documentada del job o SQL usado.
  4. Si esa evidencia no existe, el sprint permanece en estado “implementado técnicamente, pero no cerrado operativamente”.

Trazabilidad: US-BE-053, US-BE-054, US-FE-062.

* * *

## D-06-052 — La elegibilidad y la vista admin solo cierran con datos reales no vacíos y consistentes (2026-04-14)

Contexto: El summary no puede darse por válido si domina el patrón “sin auditoría reciente”, y la vista `/v2/admin/fase1-operational` no puede considerarse cerrada si solo fue validada con estructura vacía o datos de prueba.

Decisión:
  1. La elegibilidad v1 y su auditoría no se considerarán cerradas solo porque la lógica exista en código.
  2. Para cerrar este frente deberá existir evidencia real de filas en `bt2_pool_eligibility_audit` sobre eventos reales de la ventana validada, con:
     * `is_eligible` o `primary_discard_reason`,
     * coverage real distinta de cero cuando aplique,
     * y desaparición del patrón dominante “sin auditoría reciente” como explicación principal.
  3. La vista admin de Fase 1 no se considerará validada mientras solo muestre estructura vacía o datos de prueba.
  4. La validación mínima de UI deberá probar consistencia entre:
     * BD,
     * endpoint summary,
     * y `/v2/admin/fase1-operational`,
     con datos reales no vacíos.

Trazabilidad: US-BE-054, US-FE-062.

* * *

## D-06-053 — El paralelo de F2 dentro de S6.3 se limita a validación real de coverage y, como máximo, una enmienda corta (2026-04-14)

Contexto: S6.3 no debe crecer para cubrir F2 completo. El único paralelo permitido dentro del sprint es validar si la regla mínima actual de elegibilidad se sostiene con datos reales.

Decisión:
  1. El único frente válido de F2 dentro de S6.3 será validar con datos reales si la regla mínima actual de elegibilidad:
     * sirve,
     * no descarta demasiado,
     * y produce un pool razonable por liga/mercado piloto.
  2. Esta validación mínima podrá usar como lectura base:
     * coverage real por liga,
     * coverage real por mercado,
     * descarte por causa principal,
     * y tamaño efectivo del pool elegible.
  3. Dentro de S6.3 no entra:
     * rediseño completo de tiers,
     * re-arquitectura grande de `ds_input`,
     * política completa de snapshot/frescura,
     * ni expansión fuerte de mercados.
  4. Si la validación real muestra que la regla mínima actual no se sostiene para este corte, el máximo permitido dentro de S6.3 será una única decisión corta adicional de ajuste mínimo, no una redefinición amplia de F2.

Trazabilidad: US-BE-055.

* * *

## D-06-054 — El cierre formal de S6.3 exige evidencia documental explícita en `EJECUCION.md` y `TASKS.md` (2026-04-14)

Contexto: El cierre real de S6.3 requiere que el pendiente final no solo exista operativamente, sino que quede evidenciado y trazado en los documentos de ejecución del sprint.

Decisión:
  1. S6.3 solo podrá cerrarse formalmente cuando `EJECUCION.md` documente explícitamente:
     * evidencia de loop oficial para picks reales,
     * evidencia de auditoría de elegibilidad sobre eventos reales,
     * evidencia de la vista admin con datos no vacíos,
     * y resultado de la validación mínima del paralelo F2.
  2. `TASKS.md` deberá reflejar ese cierre restante con tasks finales marcables y evidencia enlazada.
  3. Si durante la validación real aparece una brecha operativa bloqueante, el sprint no se cierra por intención; deberá quedar como pendiente explícito o nueva task antes del cierre formal.
  4. La resolución final permitida para S6.3 será solo una de estas dos:
     * “cerrado realmente”, con evidencia completa;
     * o “implementado pero no cerrado operativamente”, con brecha explícita documentada.

Trazabilidad: US-BE-053, US-BE-054, US-BE-055, US-FE-062.

* * *

Creación: 2026-04-14 — decisiones puntuales para cierre real de S6.3.
Pendiente siguiente artefacto: `US_CIERRE_S6_3.md`.
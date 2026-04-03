## Identidad Visual (BetTracker 2.0)

### 1. Concepto central: "Zurich Calm"

- **Metafora**: terminal de banca privada suiza, no casa de apuestas.
- **Objetivo**: transmitir sobriedad, seguridad y disciplina. La UI acompana decisiones racionales sobre el bankroll, no impulsa apuestas reactivas.

#### Atributos clave

- **Minimalismo institucional**  
  - Espacios en blanco generosos para reducir carga cognitiva.  
  - Jerarquias de informacion claras (titulo → dato critico → explicacion humana).

- **Friccion deliberada**  
  - Uso intencional de checklists, confirmaciones y pasos extra cuando hay riesgo de sobre-apuesta.  
  - La interfaz debe invitar a hacer una pausa, no a hacer click rapido.

- **Autoridad numerica**  
  - La data es el centro del bunker: cuotas, ROI, drawdown y DP son protagonistas, no adornos.  
  - Toda metrica tecnica debe tener su traduccion humana (alineada con `00_IDENTIDAD_PROYECTO.md`).

---

### 2. Sistema de diseno (tokens)

#### Paleta de colores (mapa a Tailwind)

- **Background (fondo)**  
  - Claro: `#F8FAFC` (gris seda / light).  
  - Oscuro: `#05070A` (Deep Slate / dark).  
  - Regla: un solo modo activo por vista (evitar mezclas extrañas de light/dark).

- **Surface (contenedores)**  
  - Base: `#FFFFFF` con bordes de `1px` en `#E2E8F0`.  
  - Uso: tarjetas, paneles, tablas, modales.  
  - Sombras solo cuando sean estrictamente necesarias; por defecto predominan los bordes.

- **Accent (accion / disciplina)**  
  - Color: `#8B5CF6` (Lavender / Vibrant Purple).  
  - Uso principal:
    - Puntos de Disciplina (DP).  
    - Botones primarios.  
    - Progreso de niveles de disciplina.  
  - No usar para dinero real ni alertas de riesgo.

- **Warning (riesgo / varianza)**  
  - Color: `#FACC15` (Amber).  
  - Uso:
    - Advertencias de exposicion.  
    - Estados de duda o decisiones no confirmadas.  
  - Evitar saturar; advertencias deben sentirse excepcionales, no ruido permanente.

- **Equity (capital real)**  
  - Color base: `#10B981` (Emerald) o tonos oro sobrios.  
  - Regla dura: **solo** se usa para representar dinero real (bankroll, equity curve en unidades monetarias).  
  - Nunca reutilizar estos tonos para DP, badges gamificados o elementos decorativos.

#### Tipografia

- **Cuerpo y UI**  
  - Fuente: `Inter` (sans-serif).  
  - Uso: labels, descripciones, botones, copy de ayuda.

- **Data y metricas**  
  - Fuente: `Geist Mono` (monospaced).  
  - Uso:
    - Cuotas.  
    - ROI.  
    - Montos de dinero.  
    - IDs de auditoria.  
  - Intencion: transmitir precision tecnica y trazabilidad.

---

### 3. Componentes de firma (Signature UI)

#### A) Contrato de Disciplina (Auth Gate)

- Pantalla de acceso obligatoria antes del dashboard.  
- Estetica de **glassmorphism sutil** (blur ligero, bordes de 1px, sin brillos agresivos).  
- Requiere validacion manual de **3 axiomas** antes de liberar el acceso:
  - Cada axioma debe ser leido y confirmado (checkbox o toggle con micro-friccion).  
  - Sin los 3 confirmados, no se muestra ningun dato operativo.

#### B) Vault Cards (Boveda)

- Layout en grid de 3 columnas en desktop (adaptable a 1–2 columnas en mobile/tablet).  
- Tarjetas con:
  - Bordes de `1px` (sin sombras pesadas).  
  - Header numerico con Geist Mono para IDs y metrica principal.

- **Estado Locked**  
  - Contenido principal desenfocado (`blur`) o parcialmente oculto.  
  - Boton de accion: `"Unlock for X DP"` usando el color accent.  
  - El usuario entiende que gasta disciplina para acceder a mas contexto, no dinero.

- **Estado Unlocked**  
  - Revela:
    - Traduccion humana de los datos ("Human Translation").  
    - Curva de equity o representacion minimalista del riesgo asociado al pick.  
  - Mantener la narrativa de bunker: sobrio, sin ruido visual extra.

#### C) Terminal de Liquidacion (Settlement)

- Interfaz tipo auditoria para cerrar picks/runs:  
  - Botones claros: **Profit**, **Loss**, **Push**.  
  - Disposicion horizontal o vertical, siempre con buena separacion para evitar errores de click.

- Campo obligatorio: **Post-Match Emotional Status**  
  - Input estructurado (ej. select + textarea corta).  
  - Se registra como parte del historial conductual y puede influir en reglas futuras.

---

### 4. Reglas de implementacion para Cursor

- **Bordes sobre sombras**  
  - Priorizar siempre bordes finos de `1px` para separar secciones.  
  - Sombras suaves solo para elementos flotantes (ej. modales), nunca para todo el layout.

- **No a la urgencia artificial**  
  - Prohibido: elementos parpadeantes, rojos agresivos, cronometros de cuenta regresiva orientados a presion psicologica.  
  - Los unicos indicadores de tiempo deben estar ligados a logica real (ej. cierre de mercado) y con diseno sobrio.

- **Visualizacion de datos**  
  - Graficas minimalistas:
    - Curvas de equity con una sola linea (single stroke) y pocos puntos clave.  
    - Sin gradientes llamativos ni rellenos innecesarios.  
  - En tablas y cards, priorizar:
    - Geist Mono para numeros.  
    - Copy humano al lado o debajo, alineado con las reglas de `00_IDENTIDAD_PROYECTO.md`.

- **Feedback de disciplina**  
  - Toda accion considerada "sana" (respetar limites, cerrar posiciones segun plan, revisar vaults sin sobreapostar) debe:
    - Disparar una micro-animacion sutil de incremento de DP (ej. `+25 DP` en el header).  
    - Mantener la estetica sobria (sin explosiones ni confeti).

---

### 7. Todo el copy debe estar en español

- Cualquier texto visible en UI (labels, botones, placeholders, títulos, tooltips, mensajes de error, estados vacíos) debe estar en **español**.
- Los nombres de métricas técnicas pueden conservar su formato (por ejemplo `ROI`, `drawdown`, `DP`), pero su explicación humana y el contexto de lectura deben ir en **español**.
- Si un ref HTML trae texto en inglés, al adaptar a React se debe traducir al español siguiendo `00_IDENTIDAD_PROYECTO.md` (regla 6: “traducción humana de datos”).

### 5. Como usar este archivo

- Este documento define el **norte visual** de BetTracker 2.0.  
- Cualquier nueva vista o componente debe revisarse contra estas reglas antes de ser implementado.  
- Si una decision de UI entra en conflicto con:
  - `00_IDENTIDAD_PROYECTO.md` (vision y principios), o  
  - este `04_IDENTIDAD_VISUAL_UI.md`,  
  entonces la decision debe documentarse en `DECISIONES.md` explicando el motivo y el impacto.


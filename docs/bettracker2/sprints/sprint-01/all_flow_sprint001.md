# 📑 all_flow_sprint001.md - Protocolo de Flujo Maestro

> **Fuente de Verdad:** Este documento orquesta la relación lógica entre las US-FE-001 a la US-FE-010 para el desarrollo en Cursor.
> **Estado:** Sprint 01 - Definición Completa de Frontend.

---

## 1. El Ciclo de Vida del Operador (User Journey)

El flujo se divide en tres fases críticas que el sistema debe respetar mediante Guards de navegación y persistencia en Zustand:

### Fase A: Onboarding y Blindaje (Setup)
* **US-FE-001 (Bunker Gate):** Acceso seguro y firma obligatoria del compromiso de disciplina.
* **US-FE-005 (The Mirror):** **Diagnóstico Situacional.** Define el `OperatorProfile` inicial (The Guardian, Sniper, Volatile) y establece el `SystemIntegrity` base antes de ver cualquier dato de mercado.
* **US-FE-002 (Treasury):** Configuración de Bankroll y Stake Unit basada en la moneda local (COP) para tangibilizar el riesgo.

### Fase B: Operativa y Santuario (Daily Loop)
* **US-FE-004 (Sanctuary):** Centro de aterrizaje por defecto. Monitoreo de paz mental (Health Snapshot) y acceso controlado a la Bóveda.
* **US-FE-003 (The Vault):** Visualización de oportunidades y desbloqueo de picks mediante el uso de Discipline Points (DP).
* **US-FE-006 (Settlement):** **Terminal de Auditoría.** Liquidación técnica del pick (Profit/Loss/Push) con reflexión emocional obligatoria de 10 caracteres mínimo. Dispara recompensa de `+25 DP`.
* **US-FE-007 (After-Action Review):** **Cierre de Estación.** Reconciliación de saldo real en casa de apuestas vs. proyectado en el búnker. Bloquea la operativa hasta el siguiente ciclo.

### Fase C: Memoria y Evolución (Analytics)
* **US-FE-008 (Strategic Ledger):** Registro inmutable y cronológico de cada auditoría realizada, permitiendo ver reflexiones pasadas.
* **US-FE-009 (Strategy & Performance):** Visualización macro de la salud del sistema. Equity Curve Performance y cumplimiento de protocolos Alpha.
* **US-FE-010 (Elite Progression):** Gestión de Rango y niveles de XP. Centro de recalibración para repetir el diagnóstico tras cumplir hitos de tiempo/actividad.

---

## 2. Reconciliación de Datos (Data Flow)

| Módulo | Emite Datos (Efecto) | Recibe Datos (Dependencia) |
| :--- | :--- | :--- |
| **US-005 Diagnostic** | `systemIntegrity`, `assignedProfile` | Requiere `hasAcceptedContract: true` |
| **US-006 Settlement** | `PNL Net`, `+25 DP`, `reflectionText` | Requiere pick activo de **US-003** |
| **US-007 AAR** | `isStationLocked`, `finalDailyScore` | Requiere picks liquidados en **US-006** |
| **US-008 Ledger** | Historial de auditorías | Lee datos persistidos de **US-006** |
| **US-009 Performance** | ROI %, Max Drawdown, Equity Curve | Procesa array de `settledPicks` del Ledger |
| **US-010 Progression** | XP, Elite Ranks, Diagnostic Unlock | Acumula DP de **US-003, 006 y 007** |

---

## 3. Instrucciones de Ejecución para Cursor

1.  **Prioridad de Stores:** Extender `useUserStore`, `useTradeStore` y crear `useBankrollStore` / `useSessionStore` antes de maquetar.
2.  **Rigor visual:** Respetar las refs en `docs/bettracker2/sprints/sprint-01/refs/` (portar tokens; sin CDN ni Material en runtime). Estética **Zurich Calm** alineada a `04_IDENTIDAD_VISUAL_UI.md`; copy en español según `00_IDENTIDAD_PROYECTO.md`.
3.  **Lógica de Guards:** Implementar los "Guards" de ruta en el orden: Auth -> Contract -> Diagnostic -> Bunker. No se permiten atajos por URL.
4.  **Tipografía:** Todo valor numérico, fecha o ID técnico DEBE usar **Geist Mono**.

---
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  /** Misma clave que WEB_API_KEY en el servidor (header X-Local-Api-Key). */
  readonly VITE_WEB_API_KEY?: string
  /** BT2_ADMIN_API_KEY — header X-BT2-Admin-Key en GET /bt2/admin/analytics/dsr-day (Sprint 06). */
  readonly VITE_BT2_ADMIN_API_KEY?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

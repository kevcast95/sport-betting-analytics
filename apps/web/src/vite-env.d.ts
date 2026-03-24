/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  /** Misma clave que WEB_API_KEY en el servidor (header X-Local-Api-Key). */
  readonly VITE_WEB_API_KEY?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

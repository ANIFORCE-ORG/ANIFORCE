/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_DEMO_MODE: string
  readonly VITE_API_BASE_URL: string
  readonly VITE_WS_URL: string
  readonly VITE_REACT_APP_URL: string
  readonly VITE_VUE_APP_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

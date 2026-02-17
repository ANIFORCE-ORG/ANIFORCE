import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(() => {
  const backendPort = process.env.VITE_BACKEND_PORT || '8010'
  const backendHost = process.env.VITE_BACKEND_HOST || '127.0.0.1'
  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    server: {
      host: '0.0.0.0',
      port: Number(process.env.VITE_FRONTEND_PORT || 3010),
      proxy: {
        '/api': {
          target: `http://${backendHost}:${backendPort}`,
          changeOrigin: true,
        },
        '/ws': {
          target: `ws://${backendHost}:${backendPort}`,
          ws: true,
        },
      },
    },
  }
})

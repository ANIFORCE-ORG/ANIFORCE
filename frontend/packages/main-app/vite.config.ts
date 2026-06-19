import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(() => {
  const backendPort = process.env.VITE_BACKEND_PORT || '8010'
  const backendHost = process.env.VITE_BACKEND_HOST || '127.0.0.1'
  const agentPort = process.env.VITE_AGENT_PORT || '8020'
  const agentHost = process.env.VITE_AGENT_HOST || '127.0.0.1'
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
      allowedHosts: [
        'localhost',
        '127.0.0.1',
        'www.aniforce.cc',
        'aniforce.cc',
      ],
      proxy: {
        '/api/agent/health': {
          target: `http://${agentHost}:${agentPort}`,
          changeOrigin: true,
          rewrite: () => '/health',
        },
        '/api/agent': {
          target: `http://${agentHost}:${agentPort}`,
          changeOrigin: true,
        },
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

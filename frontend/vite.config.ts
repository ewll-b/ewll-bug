import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_TARGET || 'http://127.0.0.1:5050'

  return {
    base: env.VITE_BASE_PATH || '/',
    plugins: [vue(), tailwindcss()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': apiTarget,
        '/attachments': apiTarget,
        '/static': apiTarget,
        '/reports/testing/export': apiTarget,
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  }
})

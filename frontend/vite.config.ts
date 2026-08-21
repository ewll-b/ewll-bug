import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    base: env.VITE_BASE_PATH || '/',
    plugins: [vue(), tailwindcss()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': 'http://127.0.0.1:5050',
        '/attachments': 'http://127.0.0.1:5050',
        '/static': 'http://127.0.0.1:5050',
        '/reports/testing/export': 'http://127.0.0.1:5050',
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  }
})

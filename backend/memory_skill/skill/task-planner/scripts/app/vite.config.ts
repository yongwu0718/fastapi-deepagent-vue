import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发模式：vite 起在 5173，/api 代理到 scripts/serve.js（8734）
// 生产模式：npm run build 产出 dist，由 scripts/serve.js 托管
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8734',
    },
  },
  build: {
    outDir: 'dist',
  },
})

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    host: true, // 监听 0.0.0.0，支持局域网 IP / SSH 端口转发访问
    port: 3000,
    strictPort: false,
    open: false, // 远程开发机无图形界面时不尝试自动打开浏览器
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
        timeout: 0,
        proxyTimeout: 0
      }
    }
  },
  preview: {
    host: true,
    port: 3000
  }
})

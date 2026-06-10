import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    allowedHosts: true,
    // Proxy all backend traffic through port 3000 so one ngrok tunnel covers everything
    proxy: {
      '/api':    { target: 'http://backend:8000', changeOrigin: true },
      '/ws':     { target: 'ws://backend:8000',   changeOrigin: true, ws: true },
      '/voice':  { target: 'http://channels:8001', changeOrigin: true },
      '/health': { target: 'http://backend:8000', changeOrigin: true },
    },
  },
})

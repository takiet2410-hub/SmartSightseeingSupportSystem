import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Before API (destinations, search, recommendations) - Port 8001
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      // Auth API (login, register, oauth) - Port 8000
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // During API (visual search) - Port 8002
      '/during': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/during/, ''),
      },
      // After API (albums, summary) - Port 8003
      '/after': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/after/, ''),
      },
    },
  },
})

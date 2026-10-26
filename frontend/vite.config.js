import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development the API runs separately on :8000; proxy /api so the browser sees one origin.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': process.env.API_URL || 'http://127.0.0.1:8000' },
  },
  build: {
    chunkSizeWarningLimit: 800, // recharts is most of the bundle; fine for an internal tool
  },
})

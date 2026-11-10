import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Frontend zawsze woła względne /api/* – w trybie dev Vite przekierowuje je do backendu,
// a w produkcji robi to nginx (patrz nginx.conf).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // Polling jest potrzebny, gdy kod jest montowany do kontenera z Windowsa/macOS.
    watch: { usePolling: process.env.VITE_USE_POLLING === 'true' },
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});

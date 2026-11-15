import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite serves the React app and proxies nothing: the API base URL is explicit.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
  },
});

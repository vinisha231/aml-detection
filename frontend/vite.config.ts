/**
 * vite.config.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Vite configuration for the AML dashboard.
 *
 * What is Vite?
 *   Vite is a build tool and dev server for modern JavaScript projects.
 *   It:
 *   - Serves your TypeScript/React files instantly in development (no bundling!)
 *   - Bundles everything into optimized files for production
 *
 * What does this config do?
 *   - Registers the React plugin (Vite needs to know we're using React/JSX)
 *   - Sets up a proxy so API calls to /api/* go to our FastAPI backend
 *     (avoids CORS issues in development)
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // Register the React plugin — enables JSX transformation and fast refresh
  plugins: [react()],

  server: {
    port: 5173,   // dev server port (http://localhost:5173)

    // Proxy configuration: in dev, /api/* calls go to our FastAPI backend
    // This avoids CORS issues during development.
    // In production, configure your web server (nginx) to do this instead.
    proxy: {
      '/queue':        'http://localhost:8000',
      '/accounts':     'http://localhost:8000',
      '/dispositions': 'http://localhost:8000',
    },
  },
});

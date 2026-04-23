/**
 * frontend/src/main.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Entry point for the React application.
 *
 * What happens here:
 *   1. React finds the <div id="root"> in index.html
 *   2. It renders our <App /> component inside it
 *   3. From that point on, React controls the entire UI
 *
 * StrictMode:
 *   React.StrictMode is a developer tool that helps catch bugs early.
 *   It runs certain functions twice in development to detect side effects.
 *   Has no effect in production.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';   // Tailwind CSS global styles

// Find the <div id="root"> in index.html and mount React there
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

/**
 * frontend/src/App.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Root component — handles routing between the three dashboard screens.
 *
 * The three screens:
 *   1. /           → Queue      (morning risk queue — where analysts start)
 *   2. /accounts/:id → AccountDetail (click into an account for full detail)
 *   3. Disposition is a modal/overlay on the AccountDetail screen
 *
 * What is React Router?
 *   React Router lets us navigate between "pages" without reloading the browser.
 *   It reads the URL and renders the right component.
 *   <BrowserRouter> enables URL-based routing.
 *   <Routes> + <Route> map URLs to components.
 *   <Link> creates clickable links that update the URL without a page reload.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Queue from './components/Queue';
import AccountDetail from './components/AccountDetail';
import Navbar from './components/Navbar';

/**
 * App is the root component that:
 *  1. Wraps everything in BrowserRouter (enables URL routing)
 *  2. Shows the Navbar on every page
 *  3. Maps URLs to the correct screen component
 */
export default function App() {
  return (
    <BrowserRouter>
      {/* Navbar stays visible on every screen */}
      <Navbar />

      {/* Main content area — changes based on the URL */}
      <main className="min-h-screen bg-gray-950 px-4 py-6 max-w-7xl mx-auto">
        <Routes>
          {/* Default route: redirect / to /queue */}
          <Route path="/" element={<Navigate to="/queue" replace />} />

          {/* Screen 1: Risk queue */}
          <Route path="/queue" element={<Queue />} />

          {/* Screen 2: Account detail — :id is a URL parameter */}
          {/* Example: /accounts/ACC_000001 */}
          <Route path="/accounts/:accountId" element={<AccountDetail />} />

          {/* Catch-all: redirect unknown URLs to queue */}
          <Route path="*" element={<Navigate to="/queue" replace />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

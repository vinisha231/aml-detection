/**
 * frontend/src/components/Navbar.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Top navigation bar — visible on every screen.
 *
 * Shows:
 *   - App name / logo
 *   - Navigation links (Queue, About)
 *   - Live stats (total accounts scored, high-risk count)
 *
 * The stats in the navbar update automatically when the API data changes.
 * We use React's useEffect + useState hooks to fetch stats from the backend.
 *
 * What are hooks?
 *   Hooks are special React functions that let you "hook into" React features.
 *   useState: stores a value that, when changed, re-renders the component.
 *   useEffect: runs code after the component renders (perfect for API calls).
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { fetchStats, StatsResponse } from '../api/client';

export default function Navbar() {
  // useLocation returns the current URL — we use it to highlight active nav link
  const location = useLocation();

  // Stats loaded from the API (null = loading, object = loaded)
  const [stats, setStats] = useState<StatsResponse | null>(null);

  // Load stats when the component first mounts (and when URL changes)
  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch(() => {
        // API not running yet — silently fail, show dashes
        setStats(null);
      });
  }, [location.pathname]); // re-fetch stats when navigating (keeps them fresh)

  return (
    <nav className="bg-gray-900 border-b border-gray-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">

        {/* ── Logo / Brand ──────────────────────────────────────────────── */}
        <div className="flex items-center gap-3">
          {/* Shield icon representing financial security */}
          <span className="text-2xl">🛡️</span>
          <div>
            <h1 className="text-white font-bold text-lg leading-none">AML Monitor</h1>
            <p className="text-gray-400 text-xs">Anti-Money Laundering Detection</p>
          </div>
        </div>

        {/* ── Navigation links ──────────────────────────────────────────── */}
        <div className="flex items-center gap-6">
          <Link
            to="/queue"
            className={`text-sm font-medium transition-colors ${
              location.pathname === '/queue'
                ? 'text-blue-400 border-b-2 border-blue-400 pb-0.5'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Risk Queue
          </Link>
        </div>

        {/* ── Live stats pills ──────────────────────────────────────────── */}
        <div className="flex items-center gap-3 text-xs">
          {stats ? (
            <>
              <StatPill
                label="High Risk"
                value={stats.high_risk_accounts}
                color="text-red-400"
              />
              <StatPill
                label="Escalated"
                value={stats.escalated}
                color="text-orange-400"
              />
              <StatPill
                label="Avg Score"
                value={`${stats.avg_score.toFixed(1)}`}
                color="text-blue-400"
              />
            </>
          ) : (
            <span className="text-gray-600 text-xs">Connect backend to see stats</span>
          )}
        </div>
      </div>
    </nav>
  );
}

/**
 * StatPill — a small badge showing one statistic.
 *
 * @param label - Short label (e.g., "High Risk")
 * @param value - The number or string to display
 * @param color - Tailwind text color class (e.g., "text-red-400")
 */
function StatPill({ label, value, color }: {
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="bg-gray-800 rounded px-2 py-1 flex items-center gap-1.5">
      <span className="text-gray-500">{label}:</span>
      <span className={`font-bold ${color}`}>{value}</span>
    </div>
  );
}

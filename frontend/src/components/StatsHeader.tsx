/**
 * frontend/src/components/StatsHeader.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Dashboard stats bar shown at the top of the Queue screen.
 *
 * Displays 4 key metrics in "card" format:
 *   1. Total accounts scored
 *   2. High-risk accounts (score ≥ 70)
 *   3. Accounts escalated today
 *   4. Average risk score across all accounts
 *
 * These metrics update every time the component renders.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React, { useState, useEffect } from 'react';
import { fetchStats, StatsResponse } from '../api/client';

export default function StatsHeader() {
  const [stats,   setStats]   = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats()
      .then(data => { setStats(data); setLoading(false); })
      .catch(()  => { setLoading(false); });
  }, []);

  if (loading) return (
    <div className="grid grid-cols-4 gap-4">
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="bg-gray-800 rounded-xl p-4 animate-pulse h-20" />
      ))}
    </div>
  );

  if (!stats) return null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard
        label="Accounts Scored"
        value={stats.scored_accounts.toLocaleString()}
        sub={`of ${stats.total_accounts.toLocaleString()} total`}
        color="text-blue-400"
        icon="📊"
      />
      <StatCard
        label="High Risk"
        value={stats.high_risk_accounts.toLocaleString()}
        sub="score ≥ 70"
        color="text-red-400"
        icon="🚨"
      />
      <StatCard
        label="Escalated"
        value={stats.escalated.toLocaleString()}
        sub="SARs in progress"
        color="text-orange-400"
        icon="🔺"
      />
      <StatCard
        label="Avg Risk Score"
        value={stats.avg_score.toFixed(1)}
        sub="across all accounts"
        color="text-purple-400"
        icon="📈"
      />
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  sub:   string;
  color: string;
  icon:  string;
}

function StatCard({ label, value, sub, color, icon }: StatCardProps) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex items-start justify-between mb-2">
        <span className="text-gray-500 text-xs uppercase tracking-wide">{label}</span>
        <span className="text-xl">{icon}</span>
      </div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-gray-600 text-xs mt-1">{sub}</div>
    </div>
  );
}

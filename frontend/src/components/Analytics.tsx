/**
 * frontend/src/components/Analytics.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Analytics view — shows false positive rate per rule.
 *
 * This screen lets the compliance team see which rules generate the most noise.
 * A rule with 90% false positive rate needs to be tuned or retired.
 * A rule with 5% false positive rate is producing high-quality alerts.
 *
 * FPR (False Positive Rate) = dismissed / (dismissed + escalated)
 * for accounts that triggered this rule.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React, { useState, useEffect } from 'react';
import { fetchFPR, FPREntry } from '../api/client';

// Human-readable labels for signal types
const SIGNAL_LABELS: Record<string, string> = {
  structuring_rule:  'Structuring Rule',
  velocity_rule:     'Velocity Anomaly',
  funnel_rule:       'Funnel Account',
  dormant_rule:      'Dormant Wakeup',
  round_number_rule: 'Round Numbers',
  graph_pagerank:    'Graph: PageRank',
  graph_community:   'Graph: Shell Cluster',
  graph_cycle:       'Graph: Round-Trip Cycle',
  graph_chain:       'Graph: Layering Chain',
};

export default function Analytics() {
  const [entries,  setEntries]  = useState<FPREntry[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState<string | null>(null);

  useEffect(() => {
    fetchFPR()
      .then(data => { setEntries(data); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  if (loading) return <div className="text-gray-400 py-8 text-center">Loading analytics...</div>;
  if (error)   return <div className="text-red-400 py-8 text-center">Error: {error}</div>;
  if (entries.length === 0) return (
    <div className="text-gray-500 py-8 text-center">
      No disposition data yet. Review some accounts first.
    </div>
  );

  return (
    <div className="space-y-4">
      <h3 className="text-white font-semibold text-lg">False Positive Rate by Rule</h3>
      <p className="text-gray-400 text-sm">
        Higher FPR = rule generates more noise. Target: below 50%.
      </p>

      <div className="space-y-3">
        {entries.map(entry => {
          const fpr      = entry.false_positive_rate;
          const fprPct   = (fpr * 100).toFixed(1);
          const barColor = fpr > 0.8 ? 'bg-red-500'
                         : fpr > 0.5 ? 'bg-orange-500'
                         : fpr > 0.3 ? 'bg-amber-500'
                         : 'bg-green-500';

          return (
            <div key={entry.signal_type} className="bg-gray-800 rounded-lg p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-white text-sm font-medium">
                  {SIGNAL_LABELS[entry.signal_type] || entry.signal_type}
                </span>
                <div className="text-right text-xs text-gray-400">
                  {entry.total_fires} fires · {entry.dismissed} dismissed
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-full rounded-full ${barColor}`}
                    style={{ width: `${fprPct}%` }}
                  />
                </div>
                <span className={`text-sm font-bold w-12 text-right ${
                  fpr > 0.7 ? 'text-red-400' : fpr > 0.4 ? 'text-amber-400' : 'text-green-400'
                }`}>
                  {fprPct}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

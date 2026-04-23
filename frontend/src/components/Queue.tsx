/**
 * frontend/src/components/Queue.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Screen 1: The Risk Queue — the analyst's morning view.
 *
 * Shows a sorted table of accounts by risk score (highest first).
 * Each row shows:
 *   - Risk score + color-coded tier badge
 *   - Account ID and holder name
 *   - Top triggered signal (e.g., "STRUCTURING")
 *   - Account type and typology
 *   - Disposition status
 *   - "Review" button → navigates to AccountDetail screen
 *
 * Features:
 *   - Pagination (50 accounts per page)
 *   - Filter by disposition (unreviewed / all / escalated / dismissed)
 *   - Filter by minimum score
 *   - Loading and error states
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchQueue, AccountSummary } from '../api/client';

// ── Risk tier color mapping ────────────────────────────────────────────────────
// Maps risk tier strings to Tailwind CSS classes for color coding
const TIER_STYLES: Record<string, string> = {
  critical: 'bg-red-900/50 text-red-300 border border-red-700',
  high:     'bg-orange-900/50 text-orange-300 border border-orange-700',
  medium:   'bg-amber-900/50 text-amber-300 border border-amber-700',
  low:      'bg-green-900/50 text-green-300 border border-green-700',
};

// Score bar color — fills a progress bar based on risk score
function scoreBarColor(score: number): string {
  if (score >= 75) return 'bg-red-500';
  if (score >= 50) return 'bg-orange-500';
  if (score >= 25) return 'bg-amber-500';
  return 'bg-green-500';
}

export default function Queue() {
  const navigate = useNavigate();

  // ── State ───────────────────────────────────────────────────────────────────
  const [accounts,    setAccounts]    = useState<AccountSummary[]>([]);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState<string | null>(null);
  const [page,        setPage]        = useState(1);
  const [hasMore,     setHasMore]     = useState(false);
  const [filter,      setFilter]      = useState<string>('unreviewed');
  const [minScore,    setMinScore]    = useState<number>(0);

  // ── Fetch accounts whenever filter or page changes ──────────────────────────
  useEffect(() => {
    setLoading(true);
    setError(null);

    fetchQueue(page, 50, minScore, filter)
      .then(response => {
        setAccounts(response.accounts);
        setHasMore(response.has_more);
        setLoading(false);
      })
      .catch(err => {
        setError(
          err.code === 'ERR_NETWORK'
            ? 'Cannot connect to API. Start the backend: uvicorn backend.api.main:app --reload'
            : `Error: ${err.message}`
        );
        setLoading(false);
      });
  }, [page, filter, minScore]);

  // Reset to page 1 when filters change
  const handleFilterChange = (newFilter: string) => {
    setFilter(newFilter);
    setPage(1);
  };

  return (
    <div className="space-y-4">

      {/* ── Page header ─────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Risk Queue</h2>
          <p className="text-gray-400 text-sm mt-1">
            Accounts sorted by risk score — highest first. Click "Review" to investigate.
          </p>
        </div>

        {/* ── Filters ─────────────────────────────────────────────────────── */}
        <div className="flex items-center gap-3">
          {/* Disposition filter */}
          <select
            value={filter}
            onChange={e => handleFilterChange(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-300"
          >
            <option value="unreviewed">Unreviewed</option>
            <option value="all">All accounts</option>
            <option value="escalated">Escalated</option>
            <option value="dismissed">Dismissed</option>
          </select>

          {/* Minimum score filter */}
          <select
            value={minScore}
            onChange={e => { setMinScore(Number(e.target.value)); setPage(1); }}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-300"
          >
            <option value={0}>All scores</option>
            <option value={25}>≥ 25 (medium+)</option>
            <option value={50}>≥ 50 (high+)</option>
            <option value={75}>≥ 75 (critical)</option>
          </select>
        </div>
      </div>

      {/* ── Loading state ───────────────────────────────────────────────── */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin text-4xl">⏳</div>
          <span className="ml-3 text-gray-400">Loading accounts...</span>
        </div>
      )}

      {/* ── Error state ─────────────────────────────────────────────────── */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-6 text-center">
          <div className="text-red-400 text-lg font-semibold mb-2">⚠ Connection Error</div>
          <pre className="text-red-300 text-sm whitespace-pre-wrap">{error}</pre>
          <div className="mt-4 text-gray-400 text-sm">
            <strong>To start the backend:</strong><br />
            <code className="bg-gray-800 px-2 py-1 rounded text-green-400">
              cd AMLDetector && uvicorn backend.api.main:app --reload
            </code>
          </div>
        </div>
      )}

      {/* ── Empty state ─────────────────────────────────────────────────── */}
      {!loading && !error && accounts.length === 0 && (
        <div className="text-center py-20 text-gray-500">
          <div className="text-5xl mb-4">✅</div>
          <p className="text-lg">No accounts in the queue.</p>
          <p className="text-sm mt-2">
            Either the pipeline hasn't run yet, or all accounts have been reviewed.
          </p>
          <div className="mt-4 text-xs text-gray-600">
            Run: <code className="bg-gray-800 px-1 rounded">python scripts/run_detection.py</code>
          </div>
        </div>
      )}

      {/* ── Accounts table ──────────────────────────────────────────────── */}
      {!loading && !error && accounts.length > 0 && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase tracking-wider">
                <th className="text-left px-4 py-3 w-32">Risk Score</th>
                <th className="text-left px-4 py-3">Account</th>
                <th className="text-left px-4 py-3">Top Signal</th>
                <th className="text-left px-4 py-3">Type</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-left px-4 py-3 w-20">Action</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((account, idx) => (
                <AccountRow
                  key={account.account_id}
                  account={account}
                  rank={idx + 1 + (page - 1) * 50}
                  onReview={() => navigate(`/accounts/${account.account_id}`)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Pagination ──────────────────────────────────────────────────── */}
      {!loading && !error && (accounts.length > 0 || page > 1) && (
        <div className="flex items-center justify-between text-sm text-gray-400">
          <span>Page {page}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 rounded bg-gray-800 disabled:opacity-40 hover:bg-gray-700 transition"
            >
              ← Previous
            </button>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={!hasMore}
              className="px-3 py-1 rounded bg-gray-800 disabled:opacity-40 hover:bg-gray-700 transition"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * AccountRow — renders one account as a table row.
 *
 * @param account  The account data
 * @param rank     Position in the sorted list (1 = highest risk)
 * @param onReview Callback when "Review" is clicked
 */
function AccountRow({
  account,
  rank,
  onReview,
}: {
  account:  AccountSummary;
  rank:     number;
  onReview: () => void;
}) {
  const score = account.risk_score ?? 0;
  const tier  = account.risk_tier ?? 'low';

  return (
    <tr
      className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors cursor-pointer"
      onClick={onReview}
    >
      {/* Risk score with progress bar */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-gray-500 text-xs w-5">{rank}</span>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-bold text-white">{score.toFixed(0)}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${TIER_STYLES[tier]}`}>
                {tier}
              </span>
            </div>
            {/* Score progress bar */}
            <div className="w-20 h-1.5 bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${scoreBarColor(score)}`}
                style={{ width: `${score}%` }}
              />
            </div>
          </div>
        </div>
      </td>

      {/* Account info */}
      <td className="px-4 py-3">
        <div className="font-mono text-blue-400 text-xs">{account.account_id}</div>
        <div className="text-white font-medium">{account.holder_name}</div>
      </td>

      {/* Top signal */}
      <td className="px-4 py-3">
        {account.top_signal ? (
          <span className="text-xs bg-purple-900/50 text-purple-300 border border-purple-700 px-2 py-0.5 rounded font-mono">
            {account.top_signal}
          </span>
        ) : (
          <span className="text-gray-600 text-xs">—</span>
        )}
      </td>

      {/* Account type */}
      <td className="px-4 py-3 text-gray-400 text-xs capitalize">
        {account.account_type}
      </td>

      {/* Disposition status */}
      <td className="px-4 py-3">
        {account.disposition === 'escalated' && (
          <span className="text-xs bg-red-900/40 text-red-300 border border-red-700/50 px-2 py-0.5 rounded">
            🔺 Escalated
          </span>
        )}
        {account.disposition === 'dismissed' && (
          <span className="text-xs bg-gray-800 text-gray-500 border border-gray-700 px-2 py-0.5 rounded">
            ✓ Dismissed
          </span>
        )}
        {!account.disposition && (
          <span className="text-xs text-gray-600">Unreviewed</span>
        )}
      </td>

      {/* Review button */}
      <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
        <button
          onClick={onReview}
          className="text-xs bg-blue-700 hover:bg-blue-600 text-white px-3 py-1 rounded transition-colors"
        >
          Review →
        </button>
      </td>
    </tr>
  );
}

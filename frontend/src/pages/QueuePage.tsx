/**
 * frontend/src/pages/QueuePage.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * The main Risk Queue page — a sortable, filterable list of accounts
 * ordered by risk score descending.
 *
 * This is the primary daily workflow for AML analysts:
 *   1. Open the queue in the morning
 *   2. Work through accounts from highest risk downward
 *   3. For each account: click to review detail, then escalate or dismiss
 *   4. Repeat until queue is cleared or end of shift
 *
 * Architecture:
 *   QueuePage owns filter state and passes it to:
 *     - FilterBar (reads/updates filters)
 *     - useQueue hook (uses filters to fetch data)
 *     - AccountTable (displays results)
 *
 *   This "lift state up" pattern keeps QueuePage as the single source
 *   of truth for filter state — no hidden copies in child components.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import FilterBar, { FilterState, DispositionFilter } from '../components/FilterBar';
import StatsHeader from '../components/StatsHeader';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import RiskBadge from '../components/RiskBadge';
import TypologyBadge from '../components/TypologyBadge';
import { useQueue } from '../hooks/useQueue';
import { formatUSD, getRiskTier } from '../utils/formatters';
import { QUEUE_PAGE_SIZE } from '../utils/constants';
import { AccountSummary } from '../api/client';

// ─── Sub-components ───────────────────────────────────────────────────────────

/** Horizontal score bar for the queue table */
function ScoreBar({ score }: { score: number }) {
  const tier = getRiskTier(score);
  const bgMap = {
    critical: 'bg-red-500',
    high:     'bg-orange-500',
    medium:   'bg-yellow-500',
    low:      'bg-gray-500',
  };

  return (
    <div className="flex items-center gap-2 w-32">
      <div className="flex-1 bg-gray-800 rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full rounded-full ${bgMap[tier]}`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="font-mono text-xs font-bold text-right w-7">
        {score.toFixed(0)}
      </span>
    </div>
  );
}

/** Disposition status dot */
function DispositionDot({ disposition }: { disposition: string | null }) {
  if (!disposition || disposition === 'pending') {
    return <span className="w-2 h-2 rounded-full bg-gray-600 inline-block" title="Pending" />;
  }
  if (disposition === 'escalated') {
    return <span className="w-2 h-2 rounded-full bg-red-500 inline-block" title="Escalated" />;
  }
  return <span className="w-2 h-2 rounded-full bg-gray-400 inline-block" title="Dismissed" />;
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function QueuePage() {
  // ── Filter state ────────────────────────────────────────────────────────────
  const [filters, setFilters] = useState<FilterState>({
    minScore:      0,
    disposition:   'all' as DispositionFilter,
    sortAscending: false,
  });

  // Current page for client-side pagination
  const [page, setPage] = useState(1);

  // ── Data fetching ───────────────────────────────────────────────────────────
  const { accounts, total, loading, error, refetch } = useQueue({
    minScore:    filters.minScore,
    disposition: filters.disposition,
    limit:       200, // fetch more than one page, sort client-side
  });

  // ── Client-side sort ────────────────────────────────────────────────────────
  // The API always returns score-descending, but we support ascending too
  const sorted = useMemo(() => {
    if (!filters.sortAscending) return accounts;
    return [...accounts].reverse();
  }, [accounts, filters.sortAscending]);

  // ── Pagination ──────────────────────────────────────────────────────────────
  const totalPages = Math.ceil(sorted.length / QUEUE_PAGE_SIZE);
  const start      = (page - 1) * QUEUE_PAGE_SIZE;
  const visible    = sorted.slice(start, start + QUEUE_PAGE_SIZE);

  // Reset to page 1 when filters change
  function handleFiltersChange(newFilters: FilterState) {
    setFilters(newFilters);
    setPage(1);
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Stats bar */}
      <StatsHeader />

      {/* Page title + count */}
      <div className="flex items-baseline justify-between">
        <h1 className="text-xl font-bold text-gray-100">Risk Queue</h1>
        {!loading && (
          <span className="text-sm text-gray-500">
            {sorted.length} account{sorted.length !== 1 ? 's' : ''}
            {filters.minScore > 0 ? ` with score ≥ ${filters.minScore}` : ''}
          </span>
        )}
      </div>

      {/* Filters */}
      <FilterBar filters={filters} onChange={handleFiltersChange} />

      {/* Content */}
      {loading && <LoadingSpinner message="Loading risk queue…" />}
      {error   && <ErrorBanner message={error} onRetry={refetch} />}

      {!loading && !error && sorted.length === 0 && (
        <div className="text-center py-16 text-gray-500">
          <p className="text-4xl mb-4">✅</p>
          <p className="text-lg font-medium text-gray-400">Queue is empty</p>
          <p className="text-sm mt-2">
            {filters.minScore > 0
              ? `No accounts with score ≥ ${filters.minScore}. Try lowering the filter.`
              : 'No accounts to review. Run the detection pipeline to populate the queue.'}
          </p>
        </div>
      )}

      {!loading && !error && visible.length > 0 && (
        <>
          {/* Table */}
          <div className="overflow-x-auto rounded-xl border border-gray-800">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-900 text-gray-500 text-xs uppercase tracking-wide">
                  <th className="text-left px-4 py-3">Account</th>
                  <th className="text-left px-4 py-3">Holder</th>
                  <th className="text-left px-4 py-3">Typology</th>
                  <th className="text-left px-4 py-3">Score</th>
                  <th className="text-left px-4 py-3">Tier</th>
                  <th className="text-center px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {visible.map((acc: AccountSummary) => (
                  <tr
                    key={acc.account_id}
                    className="bg-gray-950 hover:bg-gray-900 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <Link
                        to={`/accounts/${acc.account_id}`}
                        className="font-mono text-xs text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        {acc.account_id}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-300 text-xs">{acc.holder_name}</td>
                    <td className="px-4 py-3">
                      <TypologyBadge typology={acc.typology} />
                    </td>
                    <td className="px-4 py-3">
                      {acc.risk_score !== null ? (
                        <ScoreBar score={acc.risk_score} />
                      ) : (
                        <span className="text-gray-600 text-xs">Unscored</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {acc.risk_score !== null && (
                        <RiskBadge tier={getRiskTier(acc.risk_score)} />
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <DispositionDot disposition={acc.disposition} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 text-xs rounded-lg bg-gray-800 text-gray-400 disabled:opacity-40 hover:bg-gray-700"
              >
                ← Prev
              </button>
              <span className="text-xs text-gray-500">Page {page} of {totalPages}</span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 text-xs rounded-lg bg-gray-800 text-gray-400 disabled:opacity-40 hover:bg-gray-700"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

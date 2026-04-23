/**
 * frontend/src/pages/AccountDetailPage.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Full account investigation page.
 *
 * Layout (top to bottom):
 *   1. Breadcrumb nav (← back to queue)
 *   2. Account header: ID, holder name, type, branch, balance
 *   3. Risk score circle + tier badge + evidence text
 *   4. Signals timeline (sorted by score desc)
 *   5. Transaction network graph (interactive force-directed)
 *   6. Transaction table (paginated, sortable)
 *   7. Disposition panel (escalate / dismiss with note)
 *
 * Data flow:
 *   useAccountDetail(accountId) → fetches from GET /accounts/{accountId}
 *   accountId comes from React Router URL params: /accounts/:accountId
 *
 *   After disposition is submitted, refetch() is called to update the
 *   account's disposition status on screen without navigating away.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';

import { useAccountDetail } from '../hooks/useAccountDetail';
import ScoreCircle from '../components/ScoreCircle';
import SignalTimeline from '../components/SignalTimeline';
import TransactionTable from '../components/TransactionTable';
import TypologyBadge from '../components/TypologyBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import { formatUSD, formatDate } from '../utils/formatters';
import { submitDisposition, undoDisposition } from '../api/client';

// ─── Sub-components ───────────────────────────────────────────────────────────

/** One labelled info field in the account metadata grid */
function InfoItem({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-gray-500 uppercase tracking-wide">{label}</dt>
      <dd className="text-sm text-gray-200 mt-0.5">{value ?? '—'}</dd>
    </div>
  );
}

// ─── Disposition panel ────────────────────────────────────────────────────────

interface DispositionPanelProps {
  accountId:   string;
  disposition: string | null;
  onSubmit:    () => void;
}

function DispositionPanel({ accountId, disposition, onSubmit }: DispositionPanelProps) {
  const [decision, setDecision] = useState<'escalated' | 'dismissed'>('escalated');
  const [note,     setNote]     = useState('');
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!note.trim()) {
      setError('Please add a note explaining your decision.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await submitDisposition(accountId, decision, note);
      onSubmit();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to submit disposition.');
    } finally {
      setLoading(false);
    }
  }

  async function handleUndo() {
    setLoading(true);
    try {
      await undoDisposition(accountId);
      onSubmit();
    } catch {
      setError('Failed to undo disposition.');
    } finally {
      setLoading(false);
    }
  }

  // ── Already dispositioned ─────────────────────────────────────────────────
  if (disposition && disposition !== 'pending') {
    return (
      <div className={`rounded-xl border p-4 ${
        disposition === 'escalated'
          ? 'bg-red-950 border-red-800'
          : 'bg-gray-900 border-gray-700'
      }`}>
        <p className={`text-sm font-semibold ${
          disposition === 'escalated' ? 'text-red-300' : 'text-gray-400'
        }`}>
          {disposition === 'escalated' ? '🔺 Escalated for SAR Filing' : '✓ Dismissed'}
        </p>
        <button
          onClick={handleUndo}
          disabled={loading}
          className="text-xs text-gray-500 hover:text-gray-300 underline mt-2 block"
        >
          {loading ? 'Undoing…' : 'Undo disposition'}
        </button>
      </div>
    );
  }

  // ── Disposition form ──────────────────────────────────────────────────────
  return (
    <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-4">
      <h3 className="text-sm font-semibold text-gray-200">Record Disposition</h3>

      {/* Decision radio buttons */}
      <div className="flex gap-4">
        {[
          { value: 'escalated', label: 'Escalate (SAR)', colour: 'text-red-400' },
          { value: 'dismissed', label: 'Dismiss',        colour: 'text-gray-400' },
        ].map(({ value, label, colour }) => (
          <label key={value} className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="decision"
              value={value}
              checked={decision === value}
              onChange={() => setDecision(value as 'escalated' | 'dismissed')}
              className="accent-blue-500"
            />
            <span className={`text-sm ${colour}`}>{label}</span>
          </label>
        ))}
      </div>

      {/* Analyst note */}
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Analyst note (required) — e.g. 'Multiple sub-threshold cash deposits over 14 days…'"
        rows={3}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-300 p-3 resize-none focus:outline-none focus:border-blue-500 placeholder-gray-600"
        required
      />

      {error && <ErrorBanner message={error} variant="inline" />}

      <button
        type="submit"
        disabled={loading || !note.trim()}
        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
          decision === 'escalated'
            ? 'bg-red-600 hover:bg-red-500 text-white'
            : 'bg-gray-700 hover:bg-gray-600 text-gray-200'
        } disabled:opacity-50`}
      >
        {loading ? 'Submitting…' : `Submit — ${decision === 'escalated' ? 'Escalate' : 'Dismiss'}`}
      </button>
    </form>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AccountDetailPage() {
  const { accountId } = useParams<{ accountId: string }>();
  const { account, loading, error, refetch } = useAccountDetail(accountId ?? '');

  if (loading) return <LoadingSpinner message={`Loading ${accountId}…`} />;
  if (error)   return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Link to="/queue" className="text-blue-400 text-sm hover:underline">← Back to queue</Link>
      <div className="mt-4"><ErrorBanner message={error} /></div>
    </div>
  );
  if (!account) return null;

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <Link to="/queue" className="text-blue-400 hover:underline">← Queue</Link>
        <span className="text-gray-600">/</span>
        <span className="font-mono text-gray-400">{accountId}</span>
      </div>

      {/* Account header */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex flex-col md:flex-row md:items-start gap-6">
          {/* Score circle */}
          {account.risk_score !== null && (
            <div className="shrink-0">
              <ScoreCircle score={account.risk_score} />
            </div>
          )}

          {/* Account metadata */}
          <div className="flex-1 space-y-4">
            <div className="flex items-start justify-between flex-wrap gap-2">
              <div>
                <h1 className="text-xl font-bold font-mono text-gray-100">
                  {account.account_id}
                </h1>
                <p className="text-gray-400 mt-0.5">{account.holder_name}</p>
              </div>
              <TypologyBadge typology={account.typology} large />
            </div>

            <dl className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <InfoItem label="Account Type"  value={account.account_type} />
              <InfoItem label="Branch"         value={account.branch} />
              <InfoItem label="Balance"        value={formatUSD(account.balance)} />
              <InfoItem label="Opened"         value={account.opened_date ? formatDate(account.opened_date) : '—'} />
              <InfoItem label="Is Suspicious"  value={account.is_suspicious ? '⚠️ Yes' : 'No'} />
              <InfoItem label="Disposition"    value={account.disposition ?? 'Pending'} />
            </dl>

            {/* Evidence text */}
            {account.evidence && (
              <div className="bg-gray-800 rounded-lg p-3">
                <p className="text-xs text-gray-400 leading-relaxed">{account.evidence}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Signals */}
      <section>
        <h2 className="text-base font-semibold text-gray-200 mb-3">
          Detection Signals ({account.signals.length})
        </h2>
        <SignalTimeline signals={account.signals} />
      </section>

      {/* Transactions */}
      <section>
        <h2 className="text-base font-semibold text-gray-200 mb-3">
          Transactions ({account.transactions.length} shown)
        </h2>
        <TransactionTable
          accountId={account.account_id}
          transactions={account.transactions}
        />
      </section>

      {/* Disposition */}
      <section>
        <h2 className="text-base font-semibold text-gray-200 mb-3">Disposition</h2>
        <DispositionPanel
          accountId={account.account_id}
          disposition={account.disposition}
          onSubmit={refetch}
        />
      </section>
    </div>
  );
}

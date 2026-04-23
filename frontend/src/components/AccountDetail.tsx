/**
 * frontend/src/components/AccountDetail.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Screen 2: Account Detail — the investigation screen.
 *
 * When an analyst clicks "Review" in the queue, they land here.
 * This screen shows everything about one account:
 *
 *   - Risk score and evidence strings (what triggered the flags)
 *   - Account information (name, type, balance, branch)
 *   - All detection signals that fired (each with score + explanation)
 *   - Transaction history (last 50 transactions)
 *   - Disposition section (Escalate to SAR / Dismiss — False Positive)
 *
 * The analyst reads this, decides what to do, and submits their decision.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  fetchAccountDetail,
  submitDisposition,
  AccountDetail as AccountDetailType,
  Signal,
  Transaction,
} from '../api/client';
import Disposition from './Disposition';

export default function AccountDetail() {
  // Get the accountId from the URL (e.g., /accounts/ACC_000001 → "ACC_000001")
  const { accountId } = useParams<{ accountId: string }>();
  const navigate = useNavigate();

  // ── State ────────────────────────────────────────────────────────────────
  const [account,  setAccount]  = useState<AccountDetailType | null>(null);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState<string | null>(null);
  const [showDisp, setShowDisp] = useState(false);  // show disposition modal?

  // ── Load account data ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!accountId) return;

    setLoading(true);
    fetchAccountDetail(accountId)
      .then(data => {
        setAccount(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.response?.status === 404
          ? `Account ${accountId} not found.`
          : `Failed to load account: ${err.message}`
        );
        setLoading(false);
      });
  }, [accountId]);

  // ── Handle disposition submission ─────────────────────────────────────────
  const handleDisposition = async (decision: 'escalated' | 'dismissed', note: string) => {
    if (!accountId) return;
    await submitDisposition(accountId, decision, note);
    // Reload account to show updated disposition
    const updated = await fetchAccountDetail(accountId);
    setAccount(updated);
    setShowDisp(false);
  };

  // ── Loading / error states ────────────────────────────────────────────────
  if (loading) return (
    <div className="flex items-center justify-center py-32 text-gray-400">
      <div className="animate-spin text-4xl mr-3">⏳</div> Loading account...
    </div>
  );

  if (error || !account) return (
    <div className="text-center py-20">
      <div className="text-red-400 text-xl mb-2">⚠ {error || 'Account not found'}</div>
      <button onClick={() => navigate('/queue')} className="text-blue-400 hover:underline">
        ← Back to queue
      </button>
    </div>
  );

  const score     = account.risk_score ?? 0;
  const riskColor = score >= 75 ? 'text-red-400'
                  : score >= 50 ? 'text-orange-400'
                  : score >= 25 ? 'text-amber-400'
                  : 'text-green-400';

  return (
    <div className="space-y-6">

      {/* ── Breadcrumb ──────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <button onClick={() => navigate('/queue')} className="hover:text-blue-400 transition-colors">
          Risk Queue
        </button>
        <span>›</span>
        <span className="text-gray-300">{account.account_id}</span>
      </div>

      {/* ── Header: Account + Score ─────────────────────────────────────── */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h2 className="text-2xl font-bold text-white">{account.holder_name}</h2>
              {account.is_suspicious && (
                <span className="text-xs bg-red-900/50 text-red-300 border border-red-700 px-2 py-0.5 rounded">
                  ⚑ Ground Truth: Dirty
                </span>
              )}
            </div>
            <div className="font-mono text-blue-400 text-sm mb-3">{account.account_id}</div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <InfoItem label="Account Type" value={account.account_type} />
              <InfoItem label="Branch"       value={account.branch} />
              <InfoItem label="Balance"      value={`$${account.balance.toLocaleString()}`} />
              <InfoItem label="Typology"     value={account.typology} />
            </div>
          </div>

          {/* Risk score circle */}
          <div className="text-center ml-6 flex-shrink-0">
            <div className={`text-5xl font-black ${riskColor}`}>
              {score.toFixed(0)}
            </div>
            <div className="text-gray-500 text-sm mt-1">/ 100</div>
            <div className="text-gray-400 text-xs mt-1">Risk Score</div>
          </div>
        </div>
      </div>

      {/* ── Detection Signals ────────────────────────────────────────────── */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h3 className="text-white font-semibold text-lg mb-4">
          🔍 Detection Signals ({account.signals.length})
        </h3>

        {account.signals.length === 0 ? (
          <p className="text-gray-500 text-sm">No signals fired on this account.</p>
        ) : (
          <div className="space-y-3">
            {account.signals.map((signal, idx) => (
              <SignalCard key={idx} signal={signal} />
            ))}
          </div>
        )}
      </div>

      {/* ── Transaction History ──────────────────────────────────────────── */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h3 className="text-white font-semibold text-lg mb-4">
          📋 Transaction History (last {account.transactions.length})
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs uppercase border-b border-gray-800">
                <th className="text-left py-2 pr-4">Date</th>
                <th className="text-left py-2 pr-4">Amount</th>
                <th className="text-left py-2 pr-4">Type</th>
                <th className="text-left py-2 pr-4">Counterparty</th>
                <th className="text-left py-2 pr-4">Description</th>
                <th className="text-left py-2">Flag</th>
              </tr>
            </thead>
            <tbody>
              {account.transactions.map(tx => (
                <TransactionRow
                  key={tx.transaction_id}
                  tx={tx}
                  myAccountId={account.account_id}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Disposition Section ──────────────────────────────────────────── */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h3 className="text-white font-semibold text-lg mb-4">⚖ Analyst Decision</h3>

        {account.disposition ? (
          /* Already decided */
          <div className="flex items-center gap-4">
            <div className={`text-lg font-bold ${
              account.disposition === 'escalated' ? 'text-red-400' : 'text-gray-400'
            }`}>
              {account.disposition === 'escalated' ? '🔺 Escalated to SAR' : '✓ Dismissed — False Positive'}
            </div>
            {account.disposition_note && (
              <div className="text-gray-400 text-sm">
                Note: "{account.disposition_note}"
              </div>
            )}
          </div>
        ) : (
          /* Not yet decided */
          <div>
            <p className="text-gray-400 text-sm mb-4">
              Review the signals above, then make your decision:
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDisp(true)}
                className="px-4 py-2 bg-red-700 hover:bg-red-600 text-white rounded-lg font-medium transition-colors"
              >
                🔺 Escalate to SAR
              </button>
              <button
                onClick={() => setShowDisp(true)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors"
              >
                ✓ Dismiss — False Positive
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Disposition Modal ────────────────────────────────────────────── */}
      {showDisp && (
        <Disposition
          accountId={account.account_id}
          holderName={account.holder_name}
          onSubmit={handleDisposition}
          onCancel={() => setShowDisp(false)}
        />
      )}
    </div>
  );
}

/** Small labeled info item used in the account header */
function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-gray-500 text-xs uppercase tracking-wide">{label}</div>
      <div className="text-white font-medium capitalize">{value}</div>
    </div>
  );
}

/** One detection signal displayed as a card */
function SignalCard({ signal }: { signal: Signal }) {
  const scoreColor = signal.score >= 70 ? 'text-red-400'
                   : signal.score >= 50 ? 'text-orange-400'
                   : signal.score >= 30 ? 'text-amber-400'
                   : 'text-green-400';

  return (
    <div className="border border-gray-700 rounded-lg p-4 bg-gray-800/50">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs bg-purple-900/60 text-purple-300 border border-purple-700 px-2 py-0.5 rounded">
            {signal.signal_type.replace(/_/g, ' ').toUpperCase()}
          </span>
          <span className="text-gray-500 text-xs">
            weight: {signal.weight.toFixed(1)} · conf: {(signal.confidence * 100).toFixed(0)}%
          </span>
        </div>
        <span className={`font-bold text-lg ${scoreColor}`}>
          {signal.score.toFixed(0)}/100
        </span>
      </div>
      <p className="text-gray-300 text-sm leading-relaxed">{signal.evidence}</p>
    </div>
  );
}

/** One transaction row */
function TransactionRow({ tx, myAccountId }: { tx: Transaction; myAccountId: string }) {
  const isOutgoing = tx.sender_account_id === myAccountId;
  const counterparty = isOutgoing ? tx.receiver_account_id : tx.sender_account_id;
  const date = new Date(tx.transaction_date).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric'
  });

  return (
    <tr className={`border-b border-gray-800/40 text-xs ${tx.is_suspicious ? 'bg-red-950/20' : ''}`}>
      <td className="py-2 pr-4 text-gray-400 whitespace-nowrap">{date}</td>
      <td className={`py-2 pr-4 font-mono font-bold ${isOutgoing ? 'text-red-400' : 'text-green-400'}`}>
        {isOutgoing ? '−' : '+'}${tx.amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}
      </td>
      <td className="py-2 pr-4 text-gray-400 capitalize">{tx.transaction_type.replace(/_/g, ' ')}</td>
      <td className="py-2 pr-4 font-mono text-blue-400">{counterparty}</td>
      <td className="py-2 pr-4 text-gray-400 max-w-xs truncate">{tx.description}</td>
      <td className="py-2">
        {tx.is_suspicious && (
          <span className="text-red-400 text-xs">⚑</span>
        )}
      </td>
    </tr>
  );
}

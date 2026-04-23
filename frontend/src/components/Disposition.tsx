/**
 * frontend/src/components/Disposition.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Screen 3 (Modal): The Disposition screen.
 *
 * This is a modal overlay that appears when the analyst clicks
 * "Escalate to SAR" or "Dismiss — False Positive" on the Account Detail screen.
 *
 * The analyst must:
 *   1. Confirm their decision (escalate or dismiss)
 *   2. Optionally write a note explaining their reasoning
 *   3. Click Submit
 *
 * Why capture notes?
 *   - Regulatory requirement: SARs need documented reasoning
 *   - False positive notes feed back into rule tuning
 *   - Audit trail for compliance reviews
 *
 * What is a "modal"?
 *   A modal is a UI component that overlays the current page.
 *   It blocks interaction with the rest of the page until dismissed.
 *   We implement it with a fixed-position dark overlay + centered card.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React, { useState } from 'react';

interface DispositionProps {
  accountId:  string;                    // which account is being disposed
  holderName: string;                    // account holder name (for display)
  onSubmit:   (decision: 'escalated' | 'dismissed', note: string) => Promise<void>;
  onCancel:   () => void;
}

export default function Disposition({
  accountId,
  holderName,
  onSubmit,
  onCancel,
}: DispositionProps) {
  // ── State ────────────────────────────────────────────────────────────────
  const [decision,    setDecision]    = useState<'escalated' | 'dismissed' | null>(null);
  const [note,        setNote]        = useState('');
  const [submitting,  setSubmitting]  = useState(false);
  const [error,       setError]       = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!decision) {
      setError('Please select a decision before submitting.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(decision, note);
    } catch (err: any) {
      setError(`Failed to submit: ${err.message}`);
      setSubmitting(false);
    }
  };

  return (
    /* ── Overlay ──────────────────────────────────────────────────────────── */
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">

      {/* ── Modal card ────────────────────────────────────────────────────── */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-lg shadow-2xl">

        {/* Header */}
        <div className="mb-6">
          <h3 className="text-white font-bold text-xl">Record Analyst Decision</h3>
          <p className="text-gray-400 text-sm mt-1">
            Account: <span className="font-mono text-blue-400">{accountId}</span>
            {' · '}{holderName}
          </p>
        </div>

        {/* Decision selection */}
        <div className="space-y-3 mb-6">
          <p className="text-gray-300 text-sm font-medium">Select decision:</p>

          <label className={`flex items-start gap-3 p-4 rounded-lg border-2 cursor-pointer transition-colors ${
            decision === 'escalated'
              ? 'border-red-600 bg-red-950/40'
              : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
          }`}>
            <input
              type="radio"
              name="decision"
              value="escalated"
              checked={decision === 'escalated'}
              onChange={() => setDecision('escalated')}
              className="mt-0.5"
            />
            <div>
              <div className="text-white font-semibold">🔺 Escalate to SAR</div>
              <div className="text-gray-400 text-xs mt-0.5">
                This account shows genuine signs of money laundering.
                A Suspicious Activity Report will be filed with FinCEN.
              </div>
            </div>
          </label>

          <label className={`flex items-start gap-3 p-4 rounded-lg border-2 cursor-pointer transition-colors ${
            decision === 'dismissed'
              ? 'border-gray-500 bg-gray-800/70'
              : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
          }`}>
            <input
              type="radio"
              name="decision"
              value="dismissed"
              checked={decision === 'dismissed'}
              onChange={() => setDecision('dismissed')}
              className="mt-0.5"
            />
            <div>
              <div className="text-white font-semibold">✓ Dismiss — False Positive</div>
              <div className="text-gray-400 text-xs mt-0.5">
                The alerts appear to have a legitimate explanation.
                This account does not require further investigation.
              </div>
            </div>
          </label>
        </div>

        {/* Note textarea */}
        <div className="mb-6">
          <label className="text-gray-300 text-sm font-medium block mb-2">
            Analyst note{' '}
            <span className="text-gray-500 font-normal">(required for escalations)</span>
          </label>
          <textarea
            value={note}
            onChange={e => setNote(e.target.value)}
            placeholder={
              decision === 'escalated'
                ? 'Explain why this account is suspicious: what pattern, what evidence, what makes you confident...'
                : 'Explain why this is a false positive: what is the legitimate explanation for the flagged behavior...'
            }
            rows={4}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300
                       placeholder:text-gray-600 focus:outline-none focus:border-blue-500 resize-none"
          />
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-4 text-red-400 text-sm bg-red-950/40 border border-red-700 rounded p-3">
            {error}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={submitting}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white rounded-lg
                       bg-gray-800 hover:bg-gray-700 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || !decision}
            className={`px-5 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-50 ${
              decision === 'escalated'
                ? 'bg-red-700 hover:bg-red-600 text-white'
                : decision === 'dismissed'
                ? 'bg-gray-600 hover:bg-gray-500 text-white'
                : 'bg-gray-700 text-gray-400 cursor-not-allowed'
            }`}
          >
            {submitting ? 'Submitting...' : 'Submit Decision'}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * frontend/src/components/AccountMetaGrid.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Responsive grid showing account metadata fields.
 *
 * Displays:
 *   - Holder name, account type, branch
 *   - Balance (formatted as USD)
 *   - Account opened date
 *   - Is suspicious flag (from data generation)
 *   - Scored at timestamp
 *
 * The "Is Suspicious" field uses the ground truth label from data generation.
 * In a real system this field would not exist — we use it for evaluation purposes.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React from 'react';
import { AccountDetail } from '../api/client';
import { formatUSD, formatDate } from '../utils/formatters';

interface AccountMetaGridProps {
  account: AccountDetail;
}

/** One labelled field */
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-gray-500 uppercase tracking-wide">{label}</dt>
      <dd className="text-sm text-gray-200 mt-0.5 font-medium">{children ?? '—'}</dd>
    </div>
  );
}

export default function AccountMetaGrid({ account }: AccountMetaGridProps) {
  return (
    <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-4">
      <Field label="Holder Name">
        {account.holder_name}
      </Field>

      <Field label="Account Type">
        <span className="font-mono text-blue-400 text-xs">
          {account.account_type}
        </span>
      </Field>

      <Field label="Branch">
        {account.branch ?? '—'}
      </Field>

      <Field label="Balance">
        <span className="text-green-400">
          {account.balance != null ? formatUSD(account.balance) : '—'}
        </span>
      </Field>

      <Field label="Opened">
        {account.opened_date ? formatDate(account.opened_date) : '—'}
      </Field>

      <Field label="Ground Truth">
        {account.is_suspicious ? (
          <span className="text-red-400 font-bold">⚠️ Suspicious (synthetic)</span>
        ) : (
          <span className="text-gray-500">Benign (synthetic)</span>
        )}
      </Field>

      <Field label="Disposition">
        {account.disposition ? (
          <span className={
            account.disposition === 'escalated'
              ? 'text-red-400'
              : account.disposition === 'dismissed'
              ? 'text-gray-400'
              : 'text-yellow-400'
          }>
            {account.disposition.charAt(0).toUpperCase() + account.disposition.slice(1)}
          </span>
        ) : (
          <span className="text-yellow-400">Pending</span>
        )}
      </Field>

      {account.disposition_note && (
        <div className="col-span-full">
          <dt className="text-xs text-gray-500 uppercase tracking-wide">Analyst Note</dt>
          <dd className="text-xs text-gray-400 mt-1 bg-gray-800 rounded-lg p-2 leading-relaxed">
            {account.disposition_note}
          </dd>
        </div>
      )}
    </dl>
  );
}

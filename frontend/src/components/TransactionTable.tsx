/**
 * frontend/src/components/TransactionTable.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Paginated table of transactions for an account.
 *
 * Shows the 50 most recent transactions with:
 *   - Date and time
 *   - Direction: IN (received money) or OUT (sent money)
 *   - Counterparty account ID
 *   - Amount, formatted as USD currency
 *   - Transaction type (CASH_DEPOSIT, WIRE, ACH, etc.)
 *   - Suspicious flag: red dot if is_suspicious = true
 *
 * Highlighting suspicious transactions helps analysts quickly spot the
 * pattern the detection engine flagged — e.g., 10 cash deposits just under
 * $10,000 will all appear highlighted if they were marked suspicious
 * during data generation.
 *
 * The component is "dumb" — it receives a list of Transaction objects
 * and just renders them. No API calls happen here.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React, { useState } from 'react';
import { Transaction } from '../api/client';

// ─── Constants ────────────────────────────────────────────────────────────────

/** Number of rows to show per page */
const PAGE_SIZE = 15;

/** USD currency formatter */
const USD = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Formats an ISO datetime string into a readable local date + time.
 * Example: "2024-03-15T14:23:00" → "Mar 15, 2024 · 2:23 PM"
 */
function formatDate(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }) + ' · ' + d.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  });
}

/**
 * Returns a short display name for transaction types.
 * The database stores them as uppercase strings like "CASH_DEPOSIT".
 */
function txTypeLabel(txType: string): string {
  const map: Record<string, string> = {
    CASH_DEPOSIT:    'Cash Dep',
    CASH_WITHDRAWAL: 'Cash W/D',
    WIRE:            'Wire',
    ACH:             'ACH',
    INTERNAL:        'Internal',
    P2P:             'P2P',
    SALARY:          'Salary',
    RENT:            'Rent',
    UTILITY:         'Utility',
    GROCERY:         'Grocery',
  };
  return map[txType] ?? txType;
}

// ─── Component ────────────────────────────────────────────────────────────────

interface TransactionTableProps {
  /** Account ID that is the subject of investigation */
  accountId: string;
  /** Full list of transactions involving this account */
  transactions: Transaction[];
}

export default function TransactionTable({
  accountId,
  transactions,
}: TransactionTableProps) {
  // Current pagination page (1-indexed for display)
  const [page, setPage] = useState(1);

  const totalPages = Math.ceil(transactions.length / PAGE_SIZE);

  // Slice the transaction array for the current page
  const start = (page - 1) * PAGE_SIZE;
  const visible = transactions.slice(start, start + PAGE_SIZE);

  if (transactions.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 text-sm">
        No transactions found for this account.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Transactions count summary */}
      <div className="text-xs text-gray-500">
        Showing {start + 1}–{Math.min(start + PAGE_SIZE, transactions.length)} of{' '}
        {transactions.length} transactions
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-gray-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900 text-gray-500 text-xs uppercase tracking-wide">
              <th className="text-left px-4 py-3">Date</th>
              <th className="text-left px-4 py-3">Dir</th>
              <th className="text-left px-4 py-3">Counterparty</th>
              <th className="text-right px-4 py-3">Amount</th>
              <th className="text-left px-4 py-3">Type</th>
              <th className="text-center px-4 py-3">Flag</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {visible.map((tx) => {
              // Determine direction: is our account the sender or receiver?
              const isSender = tx.sender_account_id === accountId;
              const counterparty = isSender
                ? tx.receiver_account_id
                : tx.sender_account_id;

              return (
                <tr
                  key={tx.transaction_id}
                  className={`
                    transition-colors hover:bg-gray-800
                    ${tx.is_suspicious ? 'bg-red-950 bg-opacity-20' : 'bg-gray-950'}
                  `}
                >
                  {/* Date */}
                  <td className="px-4 py-2 text-gray-400 text-xs whitespace-nowrap">
                    {formatDate(tx.transaction_date)}
                  </td>

                  {/* Direction badge */}
                  <td className="px-4 py-2">
                    <span
                      className={`
                        text-xs font-bold px-2 py-0.5 rounded-full
                        ${isSender
                          ? 'bg-red-900 text-red-300'    // outgoing = red (money leaving)
                          : 'bg-green-900 text-green-300' // incoming = green (money arriving)
                        }
                      `}
                    >
                      {isSender ? 'OUT' : 'IN'}
                    </span>
                  </td>

                  {/* Counterparty account ID */}
                  <td className="px-4 py-2 font-mono text-xs text-blue-400">
                    {counterparty}
                  </td>

                  {/* Amount — red for outgoing, green for incoming */}
                  <td
                    className={`px-4 py-2 text-right font-mono font-bold ${
                      isSender ? 'text-red-300' : 'text-green-300'
                    }`}
                  >
                    {isSender ? '-' : '+'}
                    {USD.format(tx.amount)}
                  </td>

                  {/* Transaction type */}
                  <td className="px-4 py-2 text-gray-500 text-xs">
                    {txTypeLabel(tx.transaction_type)}
                  </td>

                  {/* Suspicious flag */}
                  <td className="px-4 py-2 text-center">
                    {tx.is_suspicious ? (
                      <span
                        className="inline-block w-2 h-2 rounded-full bg-red-500"
                        title="Marked suspicious during data generation"
                      />
                    ) : (
                      <span className="inline-block w-2 h-2 rounded-full bg-gray-700" />
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 text-xs rounded-lg bg-gray-800 text-gray-400 disabled:opacity-40 hover:bg-gray-700 transition-colors"
          >
            ← Prev
          </button>
          <span className="text-xs text-gray-500">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 text-xs rounded-lg bg-gray-800 text-gray-400 disabled:opacity-40 hover:bg-gray-700 transition-colors"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * frontend/src/components/FilterBar.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Filter controls for the Risk Queue page.
 *
 * Exposes three filter parameters:
 *   1. Minimum score  — slider 0–100 (default 0, show all)
 *   2. Disposition    — dropdown: All / Pending / Escalated / Dismissed
 *   3. Sort order     — Score descending (default) or ascending
 *
 * Design pattern:
 *   The parent component (Queue.tsx) owns the filter state.
 *   FilterBar is a "controlled" component — it reads state via props
 *   and reports changes via callback functions (onChange handlers).
 *   This keeps all data-fetching logic in Queue.tsx, not here.
 *
 * Why controlled components?
 *   Makes testing easier (just check the callback was called with right args),
 *   keeps the UI in sync with URL state if we add routing later, and avoids
 *   duplicate state that can get out of sync.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React from 'react';

// ─── Types ────────────────────────────────────────────────────────────────────

export type DispositionFilter = 'all' | 'pending' | 'escalated' | 'dismissed';

export interface FilterState {
  minScore: number;
  disposition: DispositionFilter;
  sortAscending: boolean;
}

interface FilterBarProps {
  /** Current filter values (controlled by parent) */
  filters: FilterState;
  /** Called whenever the user changes any filter */
  onChange: (newFilters: FilterState) => void;
}

// ─── Disposition options for the dropdown ────────────────────────────────────

const DISPOSITION_OPTIONS: { value: DispositionFilter; label: string }[] = [
  { value: 'all',       label: 'All Accounts'   },
  { value: 'pending',   label: 'Pending Review'  },
  { value: 'escalated', label: 'Escalated (SAR)' },
  { value: 'dismissed', label: 'Dismissed'       },
];

// ─── Component ────────────────────────────────────────────────────────────────

export default function FilterBar({ filters, onChange }: FilterBarProps) {
  /** Helper: update one field and call onChange with the merged state */
  function update(patch: Partial<FilterState>) {
    onChange({ ...filters, ...patch });
  }

  return (
    <div className="flex flex-wrap items-center gap-4 bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
      {/* ── Min Score Slider ─────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 flex-1 min-w-[200px]">
        <label className="text-xs text-gray-500 whitespace-nowrap">
          Min Score
        </label>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={filters.minScore}
          onChange={(e) => update({ minScore: Number(e.target.value) })}
          className="flex-1 accent-blue-500 cursor-pointer"
          aria-label="Minimum risk score filter"
        />
        {/* Score value display — colour-coded by tier */}
        <span
          className={`text-sm font-bold font-mono w-8 text-right ${
            filters.minScore >= 90 ? 'text-red-400'    :
            filters.minScore >= 70 ? 'text-orange-400' :
            filters.minScore >= 40 ? 'text-yellow-400' :
                                     'text-gray-400'
          }`}
        >
          {filters.minScore}
        </span>
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-gray-700 hidden sm:block" />

      {/* ── Disposition Dropdown ─────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <label className="text-xs text-gray-500 whitespace-nowrap">
          Status
        </label>
        <select
          value={filters.disposition}
          onChange={(e) => update({ disposition: e.target.value as DispositionFilter })}
          className="bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded-lg px-3 py-1.5 cursor-pointer focus:outline-none focus:border-blue-500"
          aria-label="Disposition filter"
        >
          {DISPOSITION_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-gray-700 hidden sm:block" />

      {/* ── Sort Order Toggle ────────────────────────────────────────────── */}
      <button
        onClick={() => update({ sortAscending: !filters.sortAscending })}
        className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-200 transition-colors px-2 py-1 rounded-lg hover:bg-gray-800"
        aria-label="Toggle sort order"
        title={filters.sortAscending ? 'Showing lowest risk first' : 'Showing highest risk first'}
      >
        <span>{filters.sortAscending ? '↑' : '↓'}</span>
        <span className="hidden sm:inline">
          {filters.sortAscending ? 'Lowest first' : 'Highest first'}
        </span>
      </button>

      {/* ── Reset button (only shown when non-default filters are active) ── */}
      {(filters.minScore > 0 || filters.disposition !== 'all' || filters.sortAscending) && (
        <button
          onClick={() =>
            onChange({ minScore: 0, disposition: 'all', sortAscending: false })
          }
          className="text-xs text-gray-500 hover:text-gray-300 underline ml-auto"
          aria-label="Reset all filters"
        >
          Reset filters
        </button>
      )}
    </div>
  );
}

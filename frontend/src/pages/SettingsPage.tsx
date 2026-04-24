/**
 * frontend/src/pages/SettingsPage.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Settings page — analyst preferences and system configuration display.
 *
 * What settings does an AML analyst need?
 *   - Alert threshold preferences (personal minimum score to show)
 *   - UI preferences (items per page, sort order)
 *   - System info (current model version, pipeline status)
 *
 * These settings are stored in localStorage using useLocalStorage hook —
 * they persist across sessions without needing a backend.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState } from 'react';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { SCORE_HIGH_MIN, STATS_POLL_INTERVAL_MS } from '../utils/constants';

export default function SettingsPage() {
  // Persist analyst preferences in localStorage
  const [minScore, setMinScore] = useLocalStorage('settings.minScore', SCORE_HIGH_MIN);
  const [pageSize, setPageSize] = useLocalStorage('settings.pageSize', 20);
  const [pollEnabled, setPollEnabled] = useLocalStorage('settings.pollEnabled', true);

  // Local state for form — only save on submit
  const [localMinScore, setLocalMinScore] = useState(String(minScore));
  const [localPageSize, setLocalPageSize] = useState(String(pageSize));
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    const parsedScore = parseFloat(localMinScore);
    const parsedPage  = parseInt(localPageSize, 10);

    if (!isNaN(parsedScore) && parsedScore >= 0 && parsedScore <= 100) {
      setMinScore(parsedScore);
    }
    if (!isNaN(parsedPage) && parsedPage >= 5 && parsedPage <= 100) {
      setPageSize(parsedPage);
    }

    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-8">

      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 text-sm mt-1">
          Analyst preferences — stored locally in your browser.
        </p>
      </div>

      {/* Alert Display section */}
      <section className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">Alert Display</h2>

        <div>
          <label className="block text-sm text-gray-300 mb-1">
            Default minimum risk score (0–100)
          </label>
          <input
            type="number"
            min={0}
            max={100}
            value={localMinScore}
            onChange={e => setLocalMinScore(e.target.value)}
            className="w-32 px-3 py-1.5 bg-gray-800 border border-gray-700
                       text-white rounded-lg text-sm focus:outline-none
                       focus:ring-1 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Alerts below this score are hidden from the queue by default.
          </p>
        </div>

        <div>
          <label className="block text-sm text-gray-300 mb-1">
            Alerts per page
          </label>
          <select
            value={localPageSize}
            onChange={e => setLocalPageSize(e.target.value)}
            className="w-32 px-3 py-1.5 bg-gray-800 border border-gray-700
                       text-white rounded-lg text-sm focus:outline-none
                       focus:ring-1 focus:ring-blue-500"
          >
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>
        </div>
      </section>

      {/* Live Updates section */}
      <section className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">Live Updates</h2>

        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={pollEnabled}
            onChange={e => setPollEnabled(e.target.checked)}
            className="w-4 h-4 accent-blue-500"
          />
          <div>
            <span className="text-sm text-gray-300">
              Auto-refresh stats every {STATS_POLL_INTERVAL_MS / 1000}s
            </span>
            <p className="text-xs text-gray-500 mt-0.5">
              When enabled, the stats header updates automatically.
            </p>
          </div>
        </label>
      </section>

      {/* System info section */}
      <section className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-3">
        <h2 className="text-lg font-semibold text-white">System Information</h2>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-400">Detection model</dt>
            <dd className="text-white font-mono">Rule-based ensemble v1.0</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-400">Rule count</dt>
            <dd className="text-white font-mono">15 rules + 6 graph signals</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-400">Settings storage</dt>
            <dd className="text-white font-mono">localStorage (browser)</dd>
          </div>
        </dl>
      </section>

      {/* Save button */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white
                     rounded-lg font-medium transition-colors"
        >
          Save Preferences
        </button>
        {saved && (
          <span className="text-green-400 text-sm font-medium animate-fade-in">
            Saved!
          </span>
        )}
      </div>
    </div>
  );
}

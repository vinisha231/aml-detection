/**
 * frontend/src/components/SearchBar.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Global account search bar for the Navbar.
 *
 * Features:
 *   - Debounced search (waits 300ms after typing before querying)
 *   - Dropdown results with account ID, name, typology, and risk score
 *   - Keyboard navigation (↑↓ to select, Enter to navigate, Esc to close)
 *   - Click anywhere outside to close the dropdown
 *
 * Why debounce?
 *   Without debouncing, every keystroke would fire an API request.
 *   Typing "ACC_001" sends 7 requests. With debounce, we wait until
 *   the user pauses (300ms) before sending — typically just 1 request.
 *   This is gentler on the server and avoids race conditions where a
 *   fast typist gets results from an earlier, shorter query.
 *
 * Implementation uses useRef for the timeout ID:
 *   - useRef persists across re-renders without triggering re-render
 *   - This is the correct pattern for side-effect timers in React
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

// ─── Types ────────────────────────────────────────────────────────────────────

interface SearchResult {
  account_id:   string;
  holder_name:  string;
  typology:     string | null;
  risk_score:   number | null;
  disposition:  string | null;
}

// ─── Score colour helper ──────────────────────────────────────────────────────

function scoreColour(score: number | null): string {
  if (score === null)  return 'text-gray-500';
  if (score >= 90) return 'text-red-400';
  if (score >= 70) return 'text-orange-400';
  if (score >= 40) return 'text-yellow-400';
  return 'text-green-400';
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function SearchBar() {
  const navigate  = useNavigate();
  const inputRef  = useRef<HTMLInputElement>(null);
  const timerRef  = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [query,    setQuery]    = useState('');
  const [results,  setResults]  = useState<SearchResult[]>([]);
  const [open,     setOpen]     = useState(false);
  const [loading,  setLoading]  = useState(false);
  const [selected, setSelected] = useState(-1); // keyboard selection index

  // ── Search function ─────────────────────────────────────────────────────────
  const runSearch = useCallback(async (q: string) => {
    if (q.trim().length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }

    setLoading(true);
    try {
      const res = await axios.get(`/search?q=${encodeURIComponent(q)}&limit=8`);
      setResults(res.data);
      setOpen(true);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Debounced input handler ─────────────────────────────────────────────────
  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const q = e.target.value;
    setQuery(q);
    setSelected(-1);

    // Clear existing timer
    if (timerRef.current) clearTimeout(timerRef.current);

    // Set new timer — will fire 300ms after the user stops typing
    timerRef.current = setTimeout(() => runSearch(q), 300);
  }

  // ── Keyboard navigation ─────────────────────────────────────────────────────
  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open || results.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (e.key === 'Enter' && selected >= 0) {
      navigateTo(results[selected].account_id);
    } else if (e.key === 'Escape') {
      setOpen(false);
      inputRef.current?.blur();
    }
  }

  // ── Navigation ──────────────────────────────────────────────────────────────
  function navigateTo(accountId: string) {
    navigate(`/accounts/${accountId}`);
    setQuery('');
    setOpen(false);
    setResults([]);
  }

  // ── Click outside to close ──────────────────────────────────────────────────
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (inputRef.current && !inputRef.current.closest('.search-container')?.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="search-container relative w-64">
      {/* Input field */}
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">
          🔍
        </span>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setOpen(true)}
          placeholder="Search accounts…"
          className="w-full bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg pl-9 pr-3 py-1.5 focus:outline-none focus:border-blue-500 placeholder-gray-600"
          aria-label="Search accounts"
          aria-expanded={open}
          role="combobox"
        />
        {loading && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="w-3 h-3 border border-gray-600 border-t-blue-400 rounded-full animate-spin" />
          </span>
        )}
      </div>

      {/* Dropdown results */}
      {open && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl overflow-hidden z-50">
          {results.map((result, idx) => (
            <button
              key={result.account_id}
              onClick={() => navigateTo(result.account_id)}
              className={`
                w-full text-left px-4 py-2.5 border-b border-gray-800 last:border-0
                hover:bg-gray-800 transition-colors
                ${selected === idx ? 'bg-gray-800' : ''}
              `}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs text-blue-400 shrink-0">
                  {result.account_id}
                </span>
                {result.risk_score !== null && (
                  <span className={`text-xs font-bold ${scoreColour(result.risk_score)}`}>
                    {result.risk_score.toFixed(0)}
                  </span>
                )}
              </div>
              <div className="text-gray-400 text-xs truncate mt-0.5">
                {result.holder_name}
                {result.typology && (
                  <span className="ml-2 text-yellow-600">· {result.typology}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* No results */}
      {open && query.length >= 2 && results.length === 0 && !loading && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded-xl p-3 text-center text-gray-500 text-xs shadow-2xl z-50">
          No accounts found for "{query}"
        </div>
      )}
    </div>
  );
}

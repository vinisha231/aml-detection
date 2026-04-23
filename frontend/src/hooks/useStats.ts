/**
 * frontend/src/hooks/useStats.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Custom React hook for fetching dashboard summary statistics.
 *
 * Fetches from GET /queue/stats which returns:
 *   - total_accounts:    number of accounts in the database
 *   - scored_accounts:   accounts with a risk score (pipeline has run)
 *   - high_risk_accounts:accounts with score ≥ 70
 *   - escalated:         accounts with disposition = 'escalated'
 *   - avg_score:         mean risk score across all scored accounts
 *
 * The stats are polled every `refreshInterval` milliseconds so the
 * dashboard stays live without requiring a page reload.
 * Set refreshInterval to 0 to disable polling.
 *
 * Used by: StatsHeader.tsx, Navbar.tsx (via StatPills)
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchStats, StatsResponse } from '../api/client';

interface UseStatsResult {
  stats: StatsResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useStats(refreshInterval = 0): UseStatsResult {
  const [stats, setStats]   = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  // Ref to store the polling interval ID so we can clear it on unmount
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchStats();
      setStats(data);
      setError(null);
    } catch (err: any) {
      setError(err?.message ?? 'Failed to load stats.');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch on mount and when trigger changes
  useEffect(() => {
    setLoading(true);
    load();
  }, [load, trigger]);

  // Set up polling if interval > 0
  useEffect(() => {
    if (refreshInterval <= 0) return;

    intervalRef.current = setInterval(load, refreshInterval);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [load, refreshInterval]);

  const refetch = useCallback(() => setTrigger((n) => n + 1), []);

  return { stats, loading, error, refetch };
}

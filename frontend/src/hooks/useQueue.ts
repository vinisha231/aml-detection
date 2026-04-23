/**
 * frontend/src/hooks/useQueue.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Custom React hook for fetching and managing the risk queue.
 *
 * What is a custom hook?
 *   A function that starts with "use" and contains React hook calls (useState,
 *   useEffect, etc.). Custom hooks let you extract stateful logic out of
 *   components so it can be reused and tested separately.
 *
 * This hook encapsulates:
 *   - Fetching accounts from GET /queue
 *   - Managing loading and error state
 *   - Automatic re-fetch when filter parameters change
 *   - Exposing a `refetch` function for manual refresh
 *
 * Usage in a component:
 *   const { accounts, loading, error, refetch } = useQueue({ minScore: 70 });
 *
 * Why a custom hook instead of putting this logic directly in Queue.tsx?
 *   - Separation of concerns: the component handles rendering, the hook
 *     handles data fetching
 *   - Reusability: other components could use the same fetching logic
 *   - Testability: the hook can be tested in isolation with mock API calls
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchQueue, AccountSummary } from '../api/client';

// ─── Types ────────────────────────────────────────────────────────────────────

interface UseQueueParams {
  /** Minimum risk score to include (0 = show all) */
  minScore?: number;
  /** Filter by disposition status */
  disposition?: string;
  /** Number of accounts to fetch */
  limit?: number;
}

interface UseQueueResult {
  /** Array of account summaries, or empty array while loading */
  accounts: AccountSummary[];
  /** Total count from the API (may be larger than accounts.length) */
  total: number;
  /** True while the API call is in flight */
  loading: boolean;
  /** Error message if the API call failed, null otherwise */
  error: string | null;
  /** Call this to manually trigger a re-fetch (e.g., after disposition) */
  refetch: () => void;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useQueue({
  minScore = 0,
  disposition = 'all',
  limit = 100,
}: UseQueueParams = {}): UseQueueResult {
  const [accounts, setAccounts] = useState<AccountSummary[]>([]);
  const [total, setTotal]       = useState(0);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);

  // A counter we increment to trigger re-fetches without changing parameters.
  // When we call refetch(), we increment this, which causes the useEffect to
  // run again because `fetchTrigger` is in its dependency array.
  const [fetchTrigger, setFetchTrigger] = useState(0);

  // The actual data-fetching effect.
  // Runs on mount and whenever any of the dependencies change.
  useEffect(() => {
    let cancelled = false; // prevents state updates after component unmounts

    setLoading(true);
    setError(null);

    fetchQueue({
      limit,
      min_score: minScore > 0 ? minScore : undefined,
      disposition: disposition !== 'all' ? disposition : undefined,
    })
      .then((data) => {
        if (!cancelled) {
          setAccounts(data.accounts);
          setTotal(data.total);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err?.message ?? 'Failed to load accounts. Is the backend running?');
          setLoading(false);
        }
      });

    // Cleanup: mark as cancelled so stale responses don't update state
    return () => { cancelled = true; };
  }, [minScore, disposition, limit, fetchTrigger]);

  // Stable refetch function — wrapped in useCallback so its identity doesn't
  // change on every render (important for dependency arrays in parent components)
  const refetch = useCallback(() => {
    setFetchTrigger((n) => n + 1);
  }, []);

  return { accounts, total, loading, error, refetch };
}

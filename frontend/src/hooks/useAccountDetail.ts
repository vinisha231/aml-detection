/**
 * frontend/src/hooks/useAccountDetail.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Custom React hook for fetching full account detail data.
 *
 * Fetches from GET /accounts/{accountId} which returns:
 *   - Account metadata (holder name, type, branch, balance)
 *   - Risk score + evidence string
 *   - All signals (structuring, velocity, graph signals, etc.)
 *   - Recent transactions (up to 50)
 *   - Current disposition status
 *
 * The hook handles:
 *   - Automatic fetch on accountId change (e.g., when navigating between accounts)
 *   - Race condition prevention (stale response guard with `cancelled` flag)
 *   - Error state with descriptive messages
 *   - `refetch` function for post-disposition refresh
 *
 * Used by: AccountDetail.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchAccountDetail, AccountDetail } from '../api/client';

interface UseAccountDetailResult {
  /** The full account detail object, or null while loading / on error */
  account: AccountDetail | null;
  /** True while the API request is in flight */
  loading: boolean;
  /** Human-readable error message, or null if no error */
  error: string | null;
  /** Trigger a fresh fetch (e.g., after a disposition is submitted) */
  refetch: () => void;
}

export function useAccountDetail(accountId: string): UseAccountDetailResult {
  const [account, setAccount] = useState<AccountDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0); // increment to re-fetch

  useEffect(() => {
    if (!accountId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchAccountDetail(accountId)
      .then((data) => {
        if (!cancelled) {
          setAccount(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          const status = err?.response?.status;
          if (status === 404) {
            setError(`Account ${accountId} not found.`);
          } else {
            setError(err?.message ?? 'Failed to load account detail.');
          }
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [accountId, trigger]);

  const refetch = useCallback(() => setTrigger((n) => n + 1), []);

  return { account, loading, error, refetch };
}

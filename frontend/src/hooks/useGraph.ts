/**
 * frontend/src/hooks/useGraph.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Custom hook for fetching the transaction network graph for an account.
 *
 * Fetches from GET /accounts/{accountId}/graph which returns:
 *   {
 *     nodes: [{ id: "ACC_001", risk_score: 75.2, typology: "structuring" }, ...],
 *     links: [{ source: "ACC_001", target: "ACC_002", weight: 50000, tx_count: 3 }, ...]
 *   }
 *
 * This data feeds directly into the GraphViewer component (react-force-graph-2d).
 *
 * Graph fetching is separate from account detail fetching because:
 *   1. Graphs can be slow to compute (NetworkX ego-network extraction)
 *   2. Users may not always need the graph (save the API call)
 *   3. Graph rendering is expensive — we load it lazily
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchAccountGraph, GraphData } from '../api/client';

interface UseGraphResult {
  /** The graph data for rendering, or null if not yet loaded / on error */
  graph:   GraphData | null;
  /** True while the graph API call is in flight */
  loading: boolean;
  /** Error message if the call failed, null otherwise */
  error:   string | null;
  /** Trigger a fresh fetch (e.g., after pipeline re-runs) */
  refetch: () => void;
}

export function useGraph(accountId: string): UseGraphResult {
  const [graph,   setGraph]   = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  useEffect(() => {
    if (!accountId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchAccountGraph(accountId)
      .then((data) => {
        if (!cancelled) {
          setGraph(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err?.message ?? 'Failed to load graph data.');
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [accountId, trigger]);

  const refetch = useCallback(() => setTrigger((n) => n + 1), []);

  return { graph, loading, error, refetch };
}

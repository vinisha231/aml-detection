/**
 * frontend/src/utils/constants.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Application-wide constants shared across components.
 *
 * Keeping constants in one file:
 *   - Prevents "magic numbers" scattered across the codebase
 *   - Centralises thresholds so a change (e.g., raising the high-risk
 *     threshold from 70 to 75) only needs to be made in one place
 *   - Serves as documentation: someone reading this file understands
 *     what each number means and why it was chosen
 * ─────────────────────────────────────────────────────────────────────────────
 */

// ─── Risk score thresholds ────────────────────────────────────────────────────
// These match TIER_THRESHOLDS in backend/detection/scoring_config.py

/** Minimum score to be classified as "medium" risk */
export const SCORE_MEDIUM_MIN = 40;

/** Minimum score to be classified as "high" risk */
export const SCORE_HIGH_MIN = 70;

/** Minimum score to be classified as "critical" risk */
export const SCORE_CRITICAL_MIN = 90;

// ─── Queue defaults ───────────────────────────────────────────────────────────

/** Default number of accounts to fetch from the queue API */
export const QUEUE_DEFAULT_LIMIT = 100;

/** Default page size for the risk queue table */
export const QUEUE_PAGE_SIZE = 20;

// ─── AML typology labels ──────────────────────────────────────────────────────
// Human-readable names for the 6 money laundering typologies implemented.

export const TYPOLOGY_LABELS: Record<string, string> = {
  structuring:   'Structuring (Smurfing)',
  layering:      'Layering (Wire Transfers)',
  funnel:        'Funnel Account',
  round_trip:    'Round-Tripping',
  shell_company: 'Shell Company Cluster',
  velocity:      'Velocity Anomaly',
};

// ─── Signal type labels ───────────────────────────────────────────────────────
// Matches the signal_type strings returned by the backend detection engine.

export const SIGNAL_LABELS: Record<string, string> = {
  structuring:     'Structuring',
  velocity:        'Velocity Anomaly',
  funnel:          'Funnel Account',
  dormant_wakeup:  'Dormant Wakeup',
  round_number:    'Round Numbers',
  graph_pagerank:  'High Centrality (PageRank)',
  graph_community: 'Isolated Cluster (Louvain)',
  graph_cycle:     'Round-Trip Cycle',
  graph_chain:     'Layering Chain',
};

// ─── Disposition options ──────────────────────────────────────────────────────

export const DISPOSITION_OPTIONS = [
  { value: 'escalated', label: 'Escalate for SAR Filing', colour: 'text-red-400'   },
  { value: 'dismissed', label: 'Dismiss (False Positive)', colour: 'text-gray-400' },
] as const;

// ─── API polling intervals ────────────────────────────────────────────────────

/** How often (ms) to refresh stats in the Navbar. 0 = no polling. */
export const STATS_POLL_INTERVAL_MS = 30_000; // 30 seconds

// ─── Graph viewer defaults ────────────────────────────────────────────────────

/** Default depth of the ego-network graph (hops from focal node) */
export const GRAPH_DEFAULT_DEPTH = 2;

/** Minimum transaction amount to include in the graph */
export const GRAPH_MIN_AMOUNT_USD = 1_000;

/**
 * frontend/src/api/client.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * API client — all calls to the FastAPI backend go through here.
 *
 * Why centralize API calls?
 *   - One place to change the base URL (dev vs prod)
 *   - Consistent error handling
 *   - TypeScript types for every response
 *   - Easy to add auth headers later
 *
 * We use axios instead of fetch() because:
 *   - Automatic JSON parsing
 *   - Better error handling (fetch doesn't throw on 4xx/5xx)
 *   - Request/response interceptors
 * ─────────────────────────────────────────────────────────────────────────────
 */

import axios from 'axios';

// Base URL for all API calls.
// In dev: http://localhost:8000 (FastAPI dev server)
// Vite's proxy config in vite.config.ts handles the routing.
const BASE_URL = 'http://localhost:8000';

// Create an axios instance with default configuration
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,              // 30 second timeout (graph building can be slow)
  headers: {
    'Content-Type': 'application/json',
  },
});

// ─── TypeScript interfaces matching backend Pydantic models ──────────────────

/** Summary of one account shown in the risk queue */
export interface AccountSummary {
  account_id:    string;
  holder_name:   string;
  account_type:  string;
  risk_score:    number | null;
  risk_tier:     'critical' | 'high' | 'medium' | 'low' | null;
  top_signal:    string | null;
  typology:      string;
  disposition:   string | null;
  scored_at:     string | null;
}

/** One transaction */
export interface Transaction {
  transaction_id:      string;
  sender_account_id:   string;
  receiver_account_id: string;
  amount:              number;
  transaction_type:    string;
  description:         string;
  transaction_date:    string;
  is_suspicious:       boolean;
  typology:            string;
}

/** One detection signal */
export interface Signal {
  signal_type:  string;
  score:        number;
  weight:       number;
  evidence:     string;
  confidence:   number;
  created_at:   string;
}

/** Full account detail (used on the Account Detail screen) */
export interface AccountDetail {
  account_id:       string;
  holder_name:      string;
  account_type:     string;
  branch:           string;
  opened_date:      string;
  balance:          number;
  is_suspicious:    boolean;
  typology:         string;
  risk_score:       number | null;
  evidence:         string | null;
  scored_at:        string | null;
  disposition:      string | null;
  disposition_note: string | null;
  disposition_at:   string | null;
  transactions:     Transaction[];
  signals:          Signal[];
}

/** Paginated queue response */
export interface QueueResponse {
  accounts:  AccountSummary[];
  total:     number;
  page:      number;
  page_size: number;
  has_more:  boolean;
}

/** Dashboard summary stats */
export interface StatsResponse {
  total_accounts:     number;
  scored_accounts:    number;
  high_risk_accounts: number;
  escalated:          number;
  avg_score:          number;
}

/** Graph data for visualization */
export interface GraphNode {
  id:          string;
  holder_name?: string;
  risk_score?:  number;
  typology?:    string;
}

export interface GraphLink {
  source:   string;
  target:   string;
  weight:   number;
  tx_count: number;
  typology: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

/** False positive rate per rule */
export interface FPREntry {
  signal_type:         string;
  total_fires:         number;
  dismissed:           number;
  false_positive_rate: number;
}

// ─── API functions ────────────────────────────────────────────────────────────

/**
 * Fetch the risk queue (paginated list of risky accounts).
 *
 * @param page        Page number (1-based)
 * @param pageSize    Accounts per page
 * @param minScore    Minimum risk score filter
 * @param disposition Filter by disposition status
 */
export async function fetchQueue(
  page = 1,
  pageSize = 50,
  minScore = 0,
  disposition = 'unreviewed'
): Promise<QueueResponse> {
  const { data } = await api.get<QueueResponse>('/queue', {
    params: { page, page_size: pageSize, min_score: minScore, disposition },
  });
  return data;
}

/**
 * Fetch summary statistics for the dashboard header.
 */
export async function fetchStats(): Promise<StatsResponse> {
  const { data } = await api.get<StatsResponse>('/queue/stats');
  return data;
}

/**
 * Fetch full account detail including transactions and signals.
 *
 * @param accountId The account ID string (e.g., "ACC_000001")
 */
export async function fetchAccountDetail(accountId: string): Promise<AccountDetail> {
  const { data } = await api.get<AccountDetail>(`/accounts/${accountId}`);
  return data;
}

/**
 * Fetch the transaction subgraph for an account (for visualization).
 *
 * @param accountId Center account ID
 * @param depth     Graph depth (1-3 hops)
 */
export async function fetchAccountGraph(accountId: string, depth = 2): Promise<GraphData> {
  const { data } = await api.get<GraphData>(`/accounts/${accountId}/graph`, {
    params: { depth },
  });
  return data;
}

/**
 * Record an analyst disposition (escalate or dismiss).
 *
 * @param accountId The account being decided on
 * @param decision  "escalated" or "dismissed"
 * @param note      Optional analyst note
 */
export async function submitDisposition(
  accountId: string,
  decision: 'escalated' | 'dismissed',
  note?: string
): Promise<void> {
  await api.post(`/dispositions/${accountId}`, { decision, note });
}

/**
 * Undo a disposition (reset to unreviewed).
 *
 * @param accountId The account to reset
 */
export async function undoDisposition(accountId: string): Promise<void> {
  await api.delete(`/dispositions/${accountId}`);
}

/**
 * Fetch false positive rate per rule.
 */
export async function fetchFPR(): Promise<FPREntry[]> {
  const { data } = await api.get<FPREntry[]>('/queue/false-positive-rates');
  return data;
}

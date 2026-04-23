/**
 * frontend/src/utils/apiHelpers.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Utility functions for working with API responses and errors.
 *
 * Centralises error handling logic so components don't need to know
 * the exact shape of the backend's error responses.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { AxiosError } from 'axios';

// ─── Error extraction ─────────────────────────────────────────────────────────

/**
 * Extract a human-readable error message from an Axios error.
 *
 * Our backend returns errors in this format:
 *   { "error": "Not Found", "detail": "Account ACC_999 not found", "status_code": 404 }
 *
 * This function extracts the most useful part for display.
 *
 * @param err  - Any error (may or may not be an AxiosError)
 * @param fallback - Default message if we can't extract a better one
 */
export function extractErrorMessage(err: unknown, fallback = 'An unexpected error occurred.'): string {
  if (!err) return fallback;

  // Axios errors have a response property
  if (isAxiosError(err)) {
    const data = err.response?.data;

    if (typeof data === 'string') return data;
    if (typeof data === 'object' && data !== null) {
      // Our backend format: { detail: "...", error: "..." }
      if ('detail' in data && typeof data.detail === 'string') return data.detail;
      if ('error' in data && typeof data.error === 'string')  return data.error;
      if ('message' in data && typeof data.message === 'string') return data.message;
    }

    // HTTP status text fallback
    if (err.response?.status === 404) return 'Resource not found.';
    if (err.response?.status === 422) return 'Invalid request data. Please check your input.';
    if (err.response?.status === 429) return 'Too many requests. Please wait a moment.';
    if (err.response?.status === 500) return 'Server error. Please try again later.';
    if (err.response?.status === 503) return 'Service temporarily unavailable.';

    if (err.message) return err.message;
  }

  // Generic Error objects
  if (err instanceof Error) return err.message;

  return fallback;
}

/**
 * Type guard for Axios errors.
 */
function isAxiosError(err: unknown): err is AxiosError {
  return typeof err === 'object' && err !== null && 'isAxiosError' in err;
}

// ─── Request helpers ──────────────────────────────────────────────────────────

/**
 * Build URL query string from an object, skipping null/undefined values.
 *
 * Example:
 *   buildQueryString({ limit: 20, min_score: null, disposition: 'all' })
 *   → "?limit=20&disposition=all"
 */
export function buildQueryString(params: Record<string, string | number | undefined | null>): string {
  const entries = Object.entries(params).filter(([, v]) => v != null && v !== '');
  if (entries.length === 0) return '';
  return '?' + entries.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join('&');
}

// ─── Response helpers ─────────────────────────────────────────────────────────

/**
 * Check if an API response indicates a successful operation.
 * Our backend uses 2xx status codes for success.
 */
export function isSuccessStatus(status: number): boolean {
  return status >= 200 && status < 300;
}

/**
 * Format a retry delay for display after a 429 Too Many Requests response.
 * Example: 1.5 → "Retry in 1.5 seconds"
 */
export function formatRetryDelay(seconds: number): string {
  return `Retry in ${seconds.toFixed(1)} second${seconds !== 1 ? 's' : ''}`;
}

/**
 * frontend/src/utils/formatters.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Utility functions for formatting data for display.
 *
 * Keeping formatters in a separate file:
 *   1. Avoids duplicating formatting logic across components
 *   2. Makes it easy to unit-test formatting without rendering React
 *   3. Centralises locale/currency decisions in one place
 *
 * All functions are pure (no side effects, no state) — given the same
 * input they always produce the same output. This makes them trivially
 * composable and testable.
 * ─────────────────────────────────────────────────────────────────────────────
 */

// ─── Currency ─────────────────────────────────────────────────────────────────

/** Intl formatter reused across calls (creating it is expensive) */
const USD_FORMATTER = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

const USD_PRECISE = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/**
 * Format a dollar amount with no cents.
 * Example: 12345.67 → "$12,346"
 */
export function formatUSD(amount: number): string {
  return USD_FORMATTER.format(amount);
}

/**
 * Format a dollar amount with cents.
 * Example: 12345.67 → "$12,345.67"
 */
export function formatUSDPrecise(amount: number): string {
  return USD_PRECISE.format(amount);
}

// ─── Dates ────────────────────────────────────────────────────────────────────

/**
 * Format an ISO date string to a human-readable date.
 * Example: "2024-03-15T14:23:00" → "Mar 15, 2024"
 */
export function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Format an ISO date string to date + time.
 * Example: "2024-03-15T14:23:00" → "Mar 15, 2024 · 2:23 PM"
 */
export function formatDateTime(isoString: string): string {
  const d = new Date(isoString);
  return (
    d.toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
    }) +
    ' · ' +
    d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
  );
}

/**
 * Returns a human-readable relative time string.
 * Example: "2 hours ago", "3 days ago", "just now"
 */
export function formatRelativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;

  const minutes = Math.floor(diffMs / 60_000);
  const hours   = Math.floor(diffMs / 3_600_000);
  const days    = Math.floor(diffMs / 86_400_000);

  if (minutes < 1)  return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24)   return `${hours}h ago`;
  if (days < 7)     return `${days}d ago`;

  return formatDate(isoString); // fall back to full date for old entries
}

// ─── Numbers ──────────────────────────────────────────────────────────────────

/**
 * Format a large number with commas.
 * Example: 1234567 → "1,234,567"
 */
export function formatNumber(n: number): string {
  return n.toLocaleString('en-US');
}

/**
 * Format a score to one decimal place.
 * Example: 87.3452 → "87.3"
 */
export function formatScore(score: number): string {
  return score.toFixed(1);
}

/**
 * Format a fraction as a percentage string.
 * Example: 0.1234 → "12.3%"
 */
export function formatPercent(fraction: number): string {
  return (fraction * 100).toFixed(1) + '%';
}

// ─── Risk tiers ───────────────────────────────────────────────────────────────

export type RiskTier = 'critical' | 'high' | 'medium' | 'low';

/**
 * Classify a numeric score into a named risk tier.
 * Matches the backend's get_risk_tier() function in scoring.py.
 */
export function getRiskTier(score: number): RiskTier {
  if (score >= 90) return 'critical';
  if (score >= 70) return 'high';
  if (score >= 40) return 'medium';
  return 'low';
}

/**
 * Returns Tailwind CSS classes for colouring a tier label.
 */
export const TIER_STYLES: Record<RiskTier, { text: string; bg: string; border: string }> = {
  critical: { text: 'text-red-400',    bg: 'bg-red-950',    border: 'border-red-700'    },
  high:     { text: 'text-orange-400', bg: 'bg-orange-950', border: 'border-orange-700' },
  medium:   { text: 'text-yellow-400', bg: 'bg-yellow-950', border: 'border-yellow-700' },
  low:      { text: 'text-green-400',  bg: 'bg-green-950',  border: 'border-green-700'  },
};

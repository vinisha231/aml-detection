/**
 * frontend/src/components/RiskBadge.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Reusable risk tier badge component.
 *
 * Used across Queue and AccountDetail to show colored tier labels.
 * Centralizing this avoids duplicating color logic in multiple components.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React from 'react';

type RiskTier = 'critical' | 'high' | 'medium' | 'low';

interface RiskBadgeProps {
  /** Risk tier string */
  tier:  RiskTier | string | null;
  /** Optional: also show the numeric score */
  score?: number | null;
  /** Size variant */
  size?: 'sm' | 'md';
}

const TIER_CONFIG: Record<RiskTier, { bg: string; text: string; border: string; label: string }> = {
  critical: { bg: 'bg-red-900/50',    text: 'text-red-300',    border: 'border-red-700',    label: 'CRITICAL' },
  high:     { bg: 'bg-orange-900/50', text: 'text-orange-300', border: 'border-orange-700', label: 'HIGH' },
  medium:   { bg: 'bg-amber-900/50',  text: 'text-amber-300',  border: 'border-amber-700',  label: 'MEDIUM' },
  low:      { bg: 'bg-green-900/50',  text: 'text-green-300',  border: 'border-green-700',  label: 'LOW' },
};

export default function RiskBadge({ tier, score, size = 'sm' }: RiskBadgeProps) {
  const config = TIER_CONFIG[(tier as RiskTier) ?? 'low'] ?? TIER_CONFIG.low;
  const sizeClass = size === 'md' ? 'text-sm px-2.5 py-1' : 'text-xs px-1.5 py-0.5';

  return (
    <span className={`inline-flex items-center gap-1 rounded font-medium border ${config.bg} ${config.text} ${config.border} ${sizeClass}`}>
      {config.label}
      {score !== undefined && score !== null && (
        <span className="opacity-80 font-normal">· {score.toFixed(0)}</span>
      )}
    </span>
  );
}

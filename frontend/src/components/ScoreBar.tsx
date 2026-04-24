/**
 * frontend/src/components/ScoreBar.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * A horizontal progress bar representing a risk score (0–100).
 *
 * Used in the queue table to give a quick visual sense of score magnitude
 * without the analyst needing to read the exact number.
 *
 * Design:
 *   - Width proportional to score (100% = score of 100)
 *   - Color follows risk tier thresholds (same as TIER_STYLES in formatters.ts)
 *   - Optional numeric label shown to the right
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { getRiskTier, TIER_STYLES } from '../utils/formatters';

interface ScoreBarProps {
  /** Risk score 0–100. */
  score: number;
  /** Whether to show the numeric score next to the bar. Default: true. */
  showLabel?: boolean;
  /** Bar height in pixels. Default: 6. */
  height?: number;
}

export default function ScoreBar({ score, showLabel = true, height = 6 }: ScoreBarProps) {
  const tier  = getRiskTier(score);
  const style = TIER_STYLES[tier];

  // Clamp score to 0–100 for safety
  const pct = Math.min(100, Math.max(0, score));

  return (
    <div className="flex items-center gap-2">
      {/* Track (gray background) */}
      <div
        className="flex-1 bg-gray-700 rounded-full overflow-hidden"
        style={{ height }}
      >
        {/* Fill (colored by tier) */}
        <div
          className={`h-full rounded-full transition-all duration-300 ${style.bar}`}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={score}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Risk score: ${score}`}
        />
      </div>

      {showLabel && (
        <span className={`text-xs font-mono font-semibold w-7 text-right ${style.text}`}>
          {Math.round(score)}
        </span>
      )}
    </div>
  );
}

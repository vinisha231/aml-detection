/**
 * frontend/src/components/StatCard.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * A reusable card for displaying a single metric with optional trend indicator.
 *
 * Used in the Analytics and Stats pages to display KPIs like:
 * - Total alerts in queue
 * - Escalation rate
 * - Average risk score
 * - Accounts flagged this week
 *
 * Design decisions:
 *   - Consistent sizing so cards line up in a grid
 *   - Color-coded trend arrows (green = good, red = bad, but "good" depends on context)
 *   - Optional subtitle for context (e.g., "vs. last 30 days")
 * ─────────────────────────────────────────────────────────────────────────────
 */

interface StatCardProps {
  /** The KPI label shown above the value. */
  label: string;
  /** The primary metric value — can be a number, percent, or formatted string. */
  value: string | number;
  /** Optional secondary text shown below the value for context. */
  subtitle?: string;
  /** Optional trend direction — affects the color of the subtitle. */
  trend?: 'up' | 'down' | 'neutral';
  /** Whether "up" is good (green) or bad (red). Default: depends on context. */
  upIsGood?: boolean;
  /** Optional icon component to show in the card header. */
  icon?: string;
}

export default function StatCard({
  label,
  value,
  subtitle,
  trend,
  upIsGood = true,
  icon,
}: StatCardProps) {

  // Determine the trend indicator color
  // "up is good" (e.g., detection rate): up=green, down=red
  // "up is bad" (e.g., false positive rate): up=red, down=green
  const trendColor = (() => {
    if (!trend || trend === 'neutral') return 'text-gray-400';
    if (trend === 'up')   return upIsGood ? 'text-green-400' : 'text-red-400';
    if (trend === 'down') return upIsGood ? 'text-red-400'   : 'text-green-400';
    return 'text-gray-400';
  })();

  const trendArrow = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→';

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      {/* Card header: label + optional icon */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-400 font-medium uppercase tracking-wide">
          {label}
        </span>
        {icon && (
          <span className="text-2xl" role="img" aria-hidden="true">
            {icon}
          </span>
        )}
      </div>

      {/* Primary metric value */}
      <div className="text-3xl font-bold text-white mb-1">
        {value}
      </div>

      {/* Optional subtitle with trend indicator */}
      {subtitle && (
        <div className={`text-sm font-medium ${trendColor}`}>
          {trend && trend !== 'neutral' && (
            <span className="mr-1">{trendArrow}</span>
          )}
          {subtitle}
        </div>
      )}
    </div>
  );
}

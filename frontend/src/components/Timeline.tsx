/**
 * frontend/src/components/Timeline.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Visual timeline for displaying disposition history and audit trail.
 *
 * Every disposition action (escalate, dismiss, re-open) is logged with a
 * timestamp. The timeline shows these in reverse-chronological order so
 * analysts can see how a case evolved.
 *
 * Why an audit trail matters:
 *   AML regulations (BSA Section 1020.320) require documentation of why a SAR
 *   was filed — or why it wasn't. The disposition history provides that audit
 *   trail. If a regulator asks "why was this account dismissed?", the analyst's
 *   note from the disposition action is the answer.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { formatDateTime } from '../utils/formatters';

export interface TimelineEvent {
  /** What happened. */
  action: string;
  /** When it happened (ISO string or Date). */
  timestamp: string;
  /** Optional analyst note or reasoning. */
  note?: string;
  /** Visual variant — affects the dot color. */
  variant?: 'default' | 'success' | 'warning' | 'danger';
}

interface TimelineProps {
  events: TimelineEvent[];
}

const DOT_COLORS: Record<string, string> = {
  default: 'bg-gray-500',
  success: 'bg-green-500',
  warning: 'bg-yellow-500',
  danger:  'bg-red-500',
};

export default function Timeline({ events }: TimelineProps) {
  if (events.length === 0) {
    return (
      <p className="text-sm text-gray-500 italic">No history available.</p>
    );
  }

  return (
    // Outer container with left padding for the vertical line
    <div className="relative pl-6">
      {/* Vertical line running down the left side */}
      <div className="absolute left-2 top-0 bottom-0 w-px bg-gray-700" />

      <div className="space-y-4">
        {events.map((event, i) => (
          <div key={i} className="relative">
            {/* Timeline dot — positioned on the vertical line */}
            <div
              className={`
                absolute -left-[18px] top-1 w-3 h-3 rounded-full border-2 border-gray-900
                ${DOT_COLORS[event.variant ?? 'default']}
              `}
            />

            {/* Event content */}
            <div>
              {/* Action label and timestamp on the same line */}
              <div className="flex items-baseline gap-2 flex-wrap">
                <span className="text-sm font-medium text-white">
                  {event.action}
                </span>
                <span className="text-xs text-gray-500">
                  {formatDateTime(event.timestamp)}
                </span>
              </div>

              {/* Optional note, indented below the action */}
              {event.note && (
                <p className="mt-1 text-sm text-gray-400 italic">
                  "{event.note}"
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

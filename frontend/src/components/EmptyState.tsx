/**
 * frontend/src/components/EmptyState.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Reusable empty state component for when a list or query has no results.
 *
 * Good empty states:
 *   - Explain WHY there's nothing to show
 *   - Suggest what the user can do next
 *   - Match the context (queue empty vs. search no results vs. no signals)
 *
 * This component is a generic foundation. Each usage provides:
 *   - icon:     An emoji or icon to make the state visually distinct
 *   - title:    Short headline ("Queue is empty")
 *   - message:  Explanation and suggested next step
 *   - action:   Optional button for the primary action
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React from 'react';

interface EmptyStateProps {
  /** Large icon/emoji displayed above the title */
  icon?: string;
  /** Short headline (1–4 words) */
  title: string;
  /** Explanatory message (1–2 sentences) */
  message?: string;
  /** Optional call-to-action button */
  action?: {
    label: string;
    onClick: () => void;
  };
}

export default function EmptyState({
  icon = '📭',
  title,
  message,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center px-4">
      {/* Icon */}
      <span
        className="text-5xl mb-4 select-none"
        role="img"
        aria-label={title}
      >
        {icon}
      </span>

      {/* Title */}
      <h3 className="text-lg font-semibold text-gray-300 mb-2">
        {title}
      </h3>

      {/* Message */}
      {message && (
        <p className="text-sm text-gray-500 max-w-sm leading-relaxed">
          {message}
        </p>
      )}

      {/* Action button */}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-6 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

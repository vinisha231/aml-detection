/**
 * frontend/src/components/ErrorBanner.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Reusable error display component.
 *
 * Shown when an API call fails or data cannot be loaded.
 * Provides a "Try again" button that triggers a retry via a callback.
 *
 * Two variants:
 *   - "banner" (default) — full-width red bar, good for page-level errors
 *   - "inline"           — compact red box, good for inside a card
 *
 * Accessibility:
 *   - role="alert" announces the error immediately to screen readers
 *   - The error icon is aria-hidden (decorative only)
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React from 'react';

interface ErrorBannerProps {
  /** The error message to display */
  message: string;
  /** Optional callback for "Try again" button. If omitted, button is hidden. */
  onRetry?: () => void;
  /** Display variant */
  variant?: 'banner' | 'inline';
}

export default function ErrorBanner({
  message,
  onRetry,
  variant = 'banner',
}: ErrorBannerProps) {
  const isBanner = variant === 'banner';

  return (
    <div
      role="alert"
      className={`
        flex items-start gap-3 rounded-xl border
        ${isBanner
          ? 'bg-red-950 border-red-800 p-4 text-red-300'
          : 'bg-gray-900 border-red-900 p-3 text-red-400'
        }
      `}
    >
      {/* Error icon */}
      <span
        aria-hidden="true"
        className="text-xl flex-shrink-0"
      >
        {isBanner ? '🚫' : '⚠️'}
      </span>

      <div className="flex-1 min-w-0">
        {/* Error message */}
        <p className={`text-sm ${isBanner ? 'font-medium' : 'text-xs'}`}>
          {message}
        </p>

        {/* Retry button */}
        {onRetry && (
          <button
            onClick={onRetry}
            className={`
              mt-2 text-xs underline opacity-80 hover:opacity-100 transition-opacity
              ${isBanner ? 'text-red-300' : 'text-red-500'}
            `}
          >
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

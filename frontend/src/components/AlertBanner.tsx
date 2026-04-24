/**
 * frontend/src/components/AlertBanner.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Dismissible inline alert banner for success, warning, error, and info messages.
 *
 * Different from ErrorBanner (which only shows errors from API calls).
 * AlertBanner is for user-facing feedback of any type, like:
 *   - "Disposition saved successfully" (success)
 *   - "Detection pipeline is running" (info)
 *   - "Rate limit reached — slow down" (warning)
 *   - "Failed to load account" (error)
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState } from 'react';

type AlertVariant = 'success' | 'error' | 'warning' | 'info';

interface AlertBannerProps {
  /** The message to display. */
  message:  string;
  /** Visual style. */
  variant?: AlertVariant;
  /** Whether to show a close (×) button. Default: true. */
  dismissible?: boolean;
  /** Optional additional CSS classes. */
  className?: string;
}

const VARIANT_STYLES: Record<AlertVariant, { bg: string; border: string; text: string; icon: string }> = {
  success: { bg: 'bg-green-950',  border: 'border-green-700', text: 'text-green-200',  icon: '✓' },
  error:   { bg: 'bg-red-950',    border: 'border-red-700',   text: 'text-red-200',    icon: '✗' },
  warning: { bg: 'bg-yellow-950', border: 'border-yellow-700',text: 'text-yellow-200', icon: '⚠' },
  info:    { bg: 'bg-blue-950',   border: 'border-blue-700',  text: 'text-blue-200',   icon: 'ℹ' },
};

export default function AlertBanner({
  message,
  variant     = 'info',
  dismissible = true,
  className   = '',
}: AlertBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  // Once dismissed, render nothing
  if (dismissed) return null;

  const styles = VARIANT_STYLES[variant];

  return (
    <div
      role="alert"
      className={`
        flex items-start gap-3 px-4 py-3 rounded-lg border
        ${styles.bg} ${styles.border} ${styles.text}
        ${className}
      `}
    >
      {/* Icon */}
      <span className="font-bold shrink-0 mt-px" aria-hidden="true">
        {styles.icon}
      </span>

      {/* Message */}
      <p className="flex-1 text-sm">{message}</p>

      {/* Dismiss button */}
      {dismissible && (
        <button
          onClick={() => setDismissed(true)}
          className="shrink-0 opacity-60 hover:opacity-100 transition-opacity text-lg leading-none"
          aria-label="Dismiss alert"
        >
          &times;
        </button>
      )}
    </div>
  );
}

/**
 * frontend/src/components/LoadingSpinner.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Reusable loading indicator shown while API requests are in flight.
 *
 * Two display modes:
 *   - "inline"    — small spinner for use inside buttons or next to text
 *   - "fullscreen"— centred spinner that fills its parent container
 *
 * The spinner is a pure CSS animation (no external dependencies).
 * It uses border-top with a contrasting colour to create the spinning effect:
 *   - 3 sides of the border are the same colour (creates the "ring")
 *   - 1 side (top) is a different colour (creates the "moving dot" illusion)
 *   - CSS animation rotates the whole element
 *
 * Accessibility:
 *   - role="status" tells screen readers this is a status indicator
 *   - aria-label provides a text description for screen readers
 *   - The visible text "Loading..." is included but visually hidden
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React from 'react';

interface LoadingSpinnerProps {
  /** Display context. Default: 'fullscreen' */
  mode?: 'inline' | 'fullscreen';
  /** Message shown below the spinner in fullscreen mode */
  message?: string;
}

export default function LoadingSpinner({
  mode = 'fullscreen',
  message = 'Loading…',
}: LoadingSpinnerProps) {
  if (mode === 'inline') {
    return (
      <span
        role="status"
        aria-label="Loading"
        className="inline-block w-4 h-4 border-2 border-gray-600 border-t-blue-400 rounded-full animate-spin"
      />
    );
  }

  // Fullscreen mode: centred in parent container
  return (
    <div
      role="status"
      aria-label={message}
      className="flex flex-col items-center justify-center py-20 gap-4"
    >
      {/* Spinner ring */}
      <div className="w-10 h-10 border-4 border-gray-700 border-t-blue-400 rounded-full animate-spin" />

      {/* Message text */}
      <p className="text-gray-500 text-sm animate-pulse">{message}</p>
    </div>
  );
}

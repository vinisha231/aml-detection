/**
 * frontend/src/components/Tooltip.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * A lightweight tooltip component for showing contextual help text.
 *
 * Why build a custom tooltip?
 *   Tooltip libraries (Tippy.js, Radix UI) add kilobytes of JS. For a simple
 *   use case — hovering over an icon to see a definition — pure CSS + a bit
 *   of React state is sufficient and keeps our bundle small.
 *
 * Usage:
 *   <Tooltip text="PageRank measures centrality in a network graph">
 *     <QuestionMarkIcon />
 *   </Tooltip>
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState, ReactNode } from 'react';

interface TooltipProps {
  /** The text to display inside the tooltip bubble. */
  text: string;
  /** The element that triggers the tooltip on hover. */
  children: ReactNode;
  /** Where to position the tooltip relative to the trigger. Default: 'top'. */
  position?: 'top' | 'bottom' | 'left' | 'right';
}

/**
 * Wraps `children` in a relative-positioned container. Hovering shows
 * the tooltip `text` in a small bubble above/below/left/right.
 */
export default function Tooltip({
  text,
  children,
  position = 'top',
}: TooltipProps) {

  // visible tracks whether to show the tooltip
  // We use state (not CSS :hover) so we can animate or add keyboard support later
  const [visible, setVisible] = useState(false);

  // Position classes for the tooltip bubble, relative to the trigger
  const positionClasses: Record<string, string> = {
    top:    'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left:   'right-full top-1/2 -translate-y-1/2 mr-2',
    right:  'left-full top-1/2 -translate-y-1/2 ml-2',
  };

  return (
    // relative so the absolutely-positioned tooltip is relative to this container
    <div
      className="relative inline-block"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      // Keyboard accessibility: show tooltip on focus (for screen readers)
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {/* The trigger element (icon, text, etc.) */}
      {children}

      {/* The tooltip bubble — only rendered when visible */}
      {visible && (
        <div
          role="tooltip"
          className={`
            absolute z-50 w-48 px-3 py-2
            bg-gray-800 text-gray-100 text-xs rounded-lg shadow-lg
            border border-gray-700 pointer-events-none
            ${positionClasses[position]}
          `}
        >
          {text}
        </div>
      )}
    </div>
  );
}

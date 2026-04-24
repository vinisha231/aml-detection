/**
 * frontend/src/components/KeyboardShortcutHint.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Displays a keyboard shortcut hint in a <kbd>-style badge.
 *
 * Analysts reviewing hundreds of alerts per day benefit from keyboard shortcuts.
 * This component makes shortcuts discoverable in the UI without cluttering it.
 *
 * Usage:
 *   <KeyboardShortcutHint keys={['Ctrl', 'K']} label="Open search" />
 * ─────────────────────────────────────────────────────────────────────────────
 */

interface KeyboardShortcutHintProps {
  /** Array of key names to show (e.g., ['Ctrl', 'K'] or ['Esc']). */
  keys: string[];
  /** Optional accessible label describing what the shortcut does. */
  label?: string;
  /** Size variant. Default: 'sm'. */
  size?: 'xs' | 'sm';
}

export default function KeyboardShortcutHint({
  keys,
  label,
  size = 'sm',
}: KeyboardShortcutHintProps) {
  const textSize = size === 'xs' ? 'text-xs' : 'text-xs';
  const padding  = size === 'xs' ? 'px-1 py-0' : 'px-1.5 py-0.5';

  return (
    <span
      className="inline-flex items-center gap-1"
      aria-label={label}
      title={label}
    >
      {keys.map((key, i) => (
        <>
          <kbd
            key={key}
            className={`
              inline-block font-mono font-medium rounded
              bg-gray-700 border border-gray-600 text-gray-300
              ${textSize} ${padding}
            `}
          >
            {key}
          </kbd>
          {i < keys.length - 1 && (
            <span key={`sep-${i}`} className="text-gray-500 text-xs">+</span>
          )}
        </>
      ))}
    </span>
  );
}

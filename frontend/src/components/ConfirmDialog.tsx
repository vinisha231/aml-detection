/**
 * frontend/src/components/ConfirmDialog.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Confirmation dialog for destructive or irreversible actions.
 *
 * Used before actions like:
 *   - Dismissing an alert (removes it from the active queue)
 *   - Escalating to SAR review (triggers compliance workflow)
 *
 * Why a separate component from Modal?
 *   ConfirmDialog is a specific pattern: "are you sure?" with confirm/cancel.
 *   Modal is generic (arbitrary content). ConfirmDialog wraps Modal and adds
 *   the standard two-button layout so it's reusable with a consistent look.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import Modal from './Modal';

interface ConfirmDialogProps {
  /** Whether the dialog is visible. */
  isOpen:         boolean;
  /** Called when user clicks Cancel or presses Escape. */
  onCancel:       () => void;
  /** Called when user clicks the confirm button. */
  onConfirm:      () => void;
  /** Title displayed at the top of the dialog. */
  title:          string;
  /** The question or explanation body text. */
  message:        string;
  /** Label for the confirm button. Default: 'Confirm'. */
  confirmLabel?:  string;
  /** Tailwind color class for the confirm button. Default: red (destructive). */
  confirmVariant?: 'danger' | 'primary';
  /** Whether the confirm action is in progress (shows loading state). */
  isLoading?:     boolean;
}

export default function ConfirmDialog({
  isOpen,
  onCancel,
  onConfirm,
  title,
  message,
  confirmLabel  = 'Confirm',
  confirmVariant = 'danger',
  isLoading     = false,
}: ConfirmDialogProps) {

  // Button styles by variant
  const confirmButtonClass =
    confirmVariant === 'danger'
      ? 'bg-red-600 hover:bg-red-500 focus:ring-red-500'
      : 'bg-blue-600 hover:bg-blue-500 focus:ring-blue-500';

  return (
    <Modal isOpen={isOpen} onClose={onCancel} title={title} className="max-w-sm">
      {/* Message body */}
      <p className="text-gray-300 text-sm mb-6">
        {message}
      </p>

      {/* Action buttons */}
      <div className="flex gap-3 justify-end">
        {/* Cancel — always safe, non-destructive */}
        <button
          onClick={onCancel}
          disabled={isLoading}
          className="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600
                     text-gray-200 text-sm font-medium transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Cancel
        </button>

        {/* Confirm — color varies by variant */}
        <button
          onClick={onConfirm}
          disabled={isLoading}
          className={`
            px-4 py-2 rounded-lg text-white text-sm font-medium
            transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2
            focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed
            ${confirmButtonClass}
          `}
        >
          {/* Show spinner while loading */}
          {isLoading ? (
            <span className="flex items-center gap-2">
              <span className="inline-block w-3 h-3 border-2 border-white
                               border-t-transparent rounded-full animate-spin" />
              Processing...
            </span>
          ) : (
            confirmLabel
          )}
        </button>
      </div>
    </Modal>
  );
}

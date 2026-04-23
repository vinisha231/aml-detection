/**
 * frontend/src/components/Modal.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Accessible modal dialog component.
 *
 * Accessibility requirements for modals (WAI-ARIA spec):
 *   1. role="dialog" and aria-modal="true" — tells screen readers this is a dialog
 *   2. aria-labelledby — points to the modal's title element
 *   3. Focus trap — keyboard focus should stay within the modal while it's open
 *   4. Escape key closes the modal
 *   5. Backdrop click closes the modal (optional but expected by users)
 *
 * We render the modal via a Portal (document.body) so it appears above all
 * other content regardless of where it's used in the component tree. Without
 * a Portal, z-index stacking contexts can clip the modal.
 *
 * Why not use a library?
 *   Radix UI or Headless UI are excellent for production. For this educational
 *   project, building it from scratch illustrates the accessibility requirements.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { ReactNode, useEffect } from 'react';
import { createPortal } from 'react-dom';

interface ModalProps {
  /** Whether the modal is currently open. */
  isOpen:   boolean;
  /** Called when the user closes the modal (Escape key or backdrop click). */
  onClose:  () => void;
  /** Text displayed in the modal header. Also used for aria-label. */
  title:    string;
  /** The modal body content. */
  children: ReactNode;
  /** Optional CSS class for the modal panel. Useful for sizing. */
  className?: string;
}

export default function Modal({
  isOpen,
  onClose,
  title,
  children,
  className = '',
}: ModalProps) {

  // Close on Escape key press (accessibility requirement)
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    // Add listener when open, remove when closed (prevent memory leaks)
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Prevent body scroll when modal is open (standard UX behavior)
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Don't render anything when closed (not just hidden — fully unmounted)
  if (!isOpen) return null;

  // createPortal renders the modal at document.body, not inside the component tree
  // This ensures z-index stacking is correct regardless of where Modal is used
  return createPortal(
    // Backdrop: semi-transparent overlay covering the entire viewport
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}   // clicking the backdrop closes the modal
      aria-hidden="true"  // the backdrop itself is decorative
    >
      {/* Modal panel — stopPropagation prevents backdrop click from firing */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className={`
          bg-gray-900 border border-gray-700 rounded-xl shadow-2xl
          w-full max-w-lg max-h-[90vh] overflow-y-auto
          ${className}
        `}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <h2 id="modal-title" className="text-lg font-semibold text-white">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
            aria-label="Close dialog"
          >
            {/* × character for close button */}
            <span className="text-2xl leading-none">&times;</span>
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-4">
          {children}
        </div>
      </div>
    </div>,

    // Portal target — append to document.body
    document.body,
  );
}

/**
 * frontend/src/components/Pagination.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Reusable pagination controls for tables and lists.
 *
 * Controlled component — parent manages current page state.
 * Renders: [← Prev] [1] [2] ... [N] [Next →]
 *
 * Shows up to MAX_PAGE_BUTTONS page numbers, with ellipsis for long ranges.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React from 'react';

interface PaginationProps {
  /** Current page (1-indexed) */
  currentPage: number;
  /** Total number of pages */
  totalPages:  number;
  /** Called when user clicks a different page */
  onPageChange: (page: number) => void;
  /** Optional: items per page label */
  itemsPerPage?: number;
  /** Optional: total item count */
  totalItems?: number;
}

const MAX_PAGE_BUTTONS = 7;

export default function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  itemsPerPage,
  totalItems,
}: PaginationProps) {
  if (totalPages <= 1) return null; // no pagination needed for single page

  // ── Generate page number array with ellipsis ──────────────────────────────
  function getPageNumbers(): (number | '...')[] {
    if (totalPages <= MAX_PAGE_BUTTONS) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }

    const pages: (number | '...')[] = [1];

    const window = 2; // pages to show on each side of current
    const start  = Math.max(2, currentPage - window);
    const end    = Math.min(totalPages - 1, currentPage + window);

    if (start > 2) pages.push('...');
    for (let i = start; i <= end; i++) pages.push(i);
    if (end < totalPages - 1) pages.push('...');

    pages.push(totalPages);
    return pages;
  }

  const pageNumbers = getPageNumbers();

  return (
    <div className="flex items-center justify-between gap-4 flex-wrap">
      {/* Item count summary */}
      {totalItems !== undefined && itemsPerPage !== undefined && (
        <span className="text-xs text-gray-500">
          Showing {Math.min((currentPage - 1) * itemsPerPage + 1, totalItems)}–
          {Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems}
        </span>
      )}

      {/* Page buttons */}
      <div className="flex items-center gap-1 ml-auto">
        {/* Previous */}
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="px-3 py-1 text-xs rounded-lg bg-gray-800 text-gray-400 disabled:opacity-40 hover:bg-gray-700 transition-colors"
          aria-label="Previous page"
        >
          ← Prev
        </button>

        {/* Page numbers */}
        {pageNumbers.map((page, idx) =>
          page === '...' ? (
            <span key={`ellipsis-${idx}`} className="px-2 text-gray-600 text-xs">…</span>
          ) : (
            <button
              key={page}
              onClick={() => onPageChange(page as number)}
              className={`
                w-8 h-7 text-xs rounded-lg transition-colors
                ${currentPage === page
                  ? 'bg-blue-600 text-white font-bold'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }
              `}
              aria-label={`Page ${page}`}
              aria-current={currentPage === page ? 'page' : undefined}
            >
              {page}
            </button>
          )
        )}

        {/* Next */}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="px-3 py-1 text-xs rounded-lg bg-gray-800 text-gray-400 disabled:opacity-40 hover:bg-gray-700 transition-colors"
          aria-label="Next page"
        >
          Next →
        </button>
      </div>
    </div>
  );
}

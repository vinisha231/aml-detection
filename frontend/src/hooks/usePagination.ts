/**
 * frontend/src/hooks/usePagination.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Hook for managing client-side pagination state.
 *
 * Why client-side pagination?
 *   Our queue can have hundreds of accounts. Rendering all of them at once
 *   creates a slow, heavy DOM. Pagination shows only a page-sized slice,
 *   keeping rendering fast.
 *
 *   We do pagination client-side (after fetching) rather than server-side
 *   because:
 *   1. The total dataset fits in memory (< 10,000 accounts typically)
 *   2. Client-side sorting and filtering needs access to all items anyway
 *   3. Avoids extra API calls on every page change
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState, useMemo } from 'react';

interface UsePaginationResult<T> {
  /** The current page's slice of items to render. */
  page: T[];
  /** Current page number (1-indexed for display). */
  currentPage: number;
  /** Total number of pages. */
  totalPages: number;
  /** Total number of items across all pages. */
  totalItems: number;
  /** Go to the next page. No-op if already on the last page. */
  nextPage: () => void;
  /** Go to the previous page. No-op if already on the first page. */
  prevPage: () => void;
  /** Jump to a specific page (1-indexed). Clamped to valid range. */
  goToPage: (n: number) => void;
  /** True if there is a next page to go to. */
  hasNext: boolean;
  /** True if there is a previous page to go to. */
  hasPrev: boolean;
  /** Reset to page 1 — call this when the items list changes (e.g., filters applied). */
  reset: () => void;
}

/**
 * Manages pagination state for a list of items.
 *
 * @param items    - The full list of items to paginate.
 * @param pageSize - How many items to show per page. Default: 15.
 * @returns        - Pagination state and navigation functions.
 */
export function usePagination<T>(
  items:    T[],
  pageSize: number = 15,
): UsePaginationResult<T> {

  // currentPage is 1-indexed to match user-facing display
  const [currentPage, setCurrentPage] = useState(1);

  // Compute derived values with useMemo so they only recalculate when
  // items or currentPage changes (not on every render)
  const totalItems = items.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  // Clamp currentPage to valid range if items list shrinks
  // e.g., if we were on page 5 but filters reduce to 2 pages
  const clampedPage = Math.min(currentPage, totalPages);

  // Extract the current page's slice from the full items array
  // Array.slice(start, end) — start inclusive, end exclusive
  const page = useMemo(() => {
    const start = (clampedPage - 1) * pageSize;  // 0-indexed start
    const end   = start + pageSize;               // 0-indexed end (exclusive)
    return items.slice(start, end);
  }, [items, clampedPage, pageSize]);

  const hasNext = clampedPage < totalPages;
  const hasPrev = clampedPage > 1;

  const nextPage = () => {
    if (hasNext) setCurrentPage(p => p + 1);
  };

  const prevPage = () => {
    if (hasPrev) setCurrentPage(p => p - 1);
  };

  const goToPage = (n: number) => {
    // Clamp to valid range [1, totalPages]
    const clamped = Math.max(1, Math.min(n, totalPages));
    setCurrentPage(clamped);
  };

  const reset = () => setCurrentPage(1);

  return {
    page,
    currentPage: clampedPage,
    totalPages,
    totalItems,
    nextPage,
    prevPage,
    goToPage,
    hasNext,
    hasPrev,
    reset,
  };
}

/**
 * frontend/src/hooks/useDebounce.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Generic debounce hook — delays updating a value until the user has stopped
 * changing it for a specified number of milliseconds.
 *
 * Why debounce?
 *   Without debounce, a search bar that calls the API on every keystroke would
 *   fire 20+ API calls for a single search query typed quickly. This wastes
 *   bandwidth, causes race conditions (older results arriving after newer ones),
 *   and degrades the user experience.
 *
 *   With a 300ms debounce, the API call only fires once the user pauses typing.
 *
 * Usage:
 *   const debouncedQuery = useDebounce(searchQuery, 300);
 *   useEffect(() => { fetchResults(debouncedQuery); }, [debouncedQuery]);
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState, useEffect } from 'react';

/**
 * Returns a debounced version of the value that only updates after the user
 * stops changing it for `delay` milliseconds.
 *
 * @param value - The value to debounce (typically a string input).
 * @param delay - How long to wait after the last change, in milliseconds.
 * @returns     The debounced value — lags behind the input by up to `delay`ms.
 */
export function useDebounce<T>(value: T, delay: number): T {
  // debouncedValue holds the "settled" version of value
  // It starts equal to value and only updates after the delay
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    // Set a timer to update the debounced value after `delay` ms
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    // Cleanup: if value changes before the timer fires, cancel the old timer
    // This is the core of debouncing — we keep resetting the clock on each change
    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]); // Re-run the effect whenever value or delay changes

  return debouncedValue;
}

/**
 * frontend/src/hooks/useLocalStorage.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Hook for persisting state in localStorage — state survives page refreshes.
 *
 * Why persist UI state?
 *   Analyst workflow: they set their filters (min score = 70, show only escalated)
 *   and then click into individual accounts to review them. Every time they
 *   navigate back to the queue, they shouldn't have to re-set their filters.
 *
 *   localStorage persists values across page refreshes and tab reloads,
 *   making filter preferences "sticky" without needing a backend.
 *
 * Type safety:
 *   localStorage only stores strings, so we JSON.stringify on write and
 *   JSON.parse on read. The generic <T> parameter ensures the returned
 *   value has the correct TypeScript type.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState } from 'react';

/**
 * A useState replacement that also persists the value in localStorage.
 *
 * @param key          - The localStorage key to use. Should be unique per use case.
 * @param initialValue - Default value if nothing is stored yet.
 * @returns            - [storedValue, setValue] — same API as useState.
 */
export function useLocalStorage<T>(
  key:          string,
  initialValue: T,
): [T, (value: T | ((prev: T) => T)) => void] {

  // Initialize state from localStorage, falling back to initialValue
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      // localStorage.getItem returns null if the key doesn't exist
      const item = window.localStorage.getItem(key);

      // If we found a stored value, parse it from JSON and return it
      // JSON.parse converts the string back to the original type
      return item !== null ? (JSON.parse(item) as T) : initialValue;
    } catch (error) {
      // localStorage can throw if:
      //   1. The stored value is not valid JSON (corrupted data)
      //   2. We're in an environment without localStorage (SSR, private mode)
      // In either case, fall back to the initial value
      console.warn(`useLocalStorage: Failed to read key "${key}":`, error);
      return initialValue;
    }
  });

  // Wrap setValue to also update localStorage on every state change
  const setValue = (value: T | ((prev: T) => T)) => {
    try {
      // Support both direct values and updater functions (same as useState)
      // e.g., setValue(42)  OR  setValue(prev => prev + 1)
      const valueToStore =
        value instanceof Function ? value(storedValue) : value;

      // Update React state
      setStoredValue(valueToStore);

      // Persist to localStorage as a JSON string
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      // localStorage can throw in private/incognito mode or when storage is full
      // We degrade gracefully — state still updates in memory, just not persisted
      console.warn(`useLocalStorage: Failed to write key "${key}":`, error);
    }
  };

  return [storedValue, setValue];
}

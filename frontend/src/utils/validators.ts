/**
 * frontend/src/utils/validators.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Input validation utilities for form fields in the analyst UI.
 *
 * Why validate on the frontend?
 *   1. Immediate feedback — show errors before the user submits
 *   2. Save API calls — don't send obviously invalid requests
 *   3. UX — "Score must be between 0 and 100" is more helpful than a 422 error
 *
 *   Note: Frontend validation is never sufficient on its own. The FastAPI
 *   backend must also validate all inputs (Pydantic handles this). Frontend
 *   validation is a UX enhancement, not a security control.
 * ─────────────────────────────────────────────────────────────────────────────
 */


// ─── Score validation ─────────────────────────────────────────────────────────

/**
 * Validate a risk score slider value.
 *
 * @param value - The score string from an input field.
 * @returns     - Error message if invalid, null if valid.
 */
export function validateScore(value: string): string | null {
  // Empty string is valid (means "no minimum score filter")
  if (value === '' || value === null || value === undefined) return null;

  const num = Number(value);

  if (isNaN(num)) return 'Score must be a number.';
  if (num < 0)    return 'Score cannot be negative.';
  if (num > 100)  return 'Score cannot exceed 100.';

  return null; // valid
}


// ─── Disposition note validation ─────────────────────────────────────────────

const MIN_NOTE_LENGTH = 10;   // Require a meaningful note, not just "ok"
const MAX_NOTE_LENGTH = 2000; // Prevent enormous notes that could be DB issues

/**
 * Validate a disposition note (the analyst's reasoning for their decision).
 *
 * @param note     - The note text.
 * @param required - If true, an empty note is an error. Default false.
 * @returns        - Error message if invalid, null if valid.
 */
export function validateDispositionNote(
  note:     string,
  required: boolean = false,
): string | null {
  const trimmed = note.trim();

  if (trimmed.length === 0) {
    return required ? 'A note is required for this disposition.' : null;
  }

  if (trimmed.length < MIN_NOTE_LENGTH) {
    return `Note must be at least ${MIN_NOTE_LENGTH} characters.`;
  }

  if (trimmed.length > MAX_NOTE_LENGTH) {
    return `Note cannot exceed ${MAX_NOTE_LENGTH} characters (currently ${trimmed.length}).`;
  }

  return null;
}


// ─── Account ID validation ────────────────────────────────────────────────────

/**
 * Validate that a string looks like a valid account ID.
 *
 * Account IDs in our system follow the pattern ACC_XXXX (alphanumeric + underscores).
 *
 * @param id - The account ID string to validate.
 * @returns  - Error message if invalid, null if valid.
 */
export function validateAccountId(id: string): string | null {
  if (!id || id.trim().length === 0) {
    return 'Account ID is required.';
  }

  // Account IDs must start with ACC_ and contain only alphanumeric + underscores
  const pattern = /^[A-Z][A-Z0-9_]+$/;
  if (!pattern.test(id)) {
    return 'Account ID must contain only uppercase letters, numbers, and underscores.';
  }

  if (id.length > 50) {
    return 'Account ID is too long (max 50 characters).';
  }

  return null;
}


// ─── Search query validation ──────────────────────────────────────────────────

/**
 * Validate a search query string.
 *
 * @param query - The search string to validate.
 * @returns     - Error message if invalid, null if valid.
 */
export function validateSearchQuery(query: string): string | null {
  if (query.trim().length === 0) {
    return null; // Empty search is fine — show all or nothing
  }

  if (query.trim().length < 2) {
    return 'Search query must be at least 2 characters.';
  }

  if (query.length > 100) {
    return 'Search query is too long (max 100 characters).';
  }

  // Prevent SQL injection characters (belt-and-suspenders — backend also sanitizes)
  const suspiciousChars = /['";<>\\]/;
  if (suspiciousChars.test(query)) {
    return 'Search query contains invalid characters.';
  }

  return null;
}

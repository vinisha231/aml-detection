/**
 * frontend/src/utils/csvExport.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Client-side CSV export utilities.
 *
 * Why client-side export?
 *   The backend provides streaming CSV export for large datasets (see export.py).
 *   But for small, in-memory tables (like the current page of results), we can
 *   generate the CSV entirely in the browser without a round-trip.
 *
 *   This is useful for:
 *   - Exporting filtered/sorted results exactly as displayed
 *   - Allowing analysts to export ad-hoc data without backend support
 *   - Working offline or when the backend is slow
 *
 * How the download works:
 *   We create a Blob (binary large object) with the CSV data, then create a
 *   temporary <a> element with a blob URL, click it programmatically, and
 *   immediately clean up. This triggers the browser's native download dialog.
 * ─────────────────────────────────────────────────────────────────────────────
 */


/**
 * Escape a value for inclusion in a CSV cell.
 *
 * CSV spec (RFC 4180) requires:
 *   - Fields containing commas, quotes, or newlines must be quoted
 *   - Literal quotes within a quoted field are escaped as ""
 *
 * @param value - Any value to escape.
 * @returns     - The value as a properly escaped CSV cell string.
 */
function escapeCsvCell(value: unknown): string {
  if (value === null || value === undefined) return '';

  const str = String(value);

  // If the value contains special characters, wrap in quotes and escape internal quotes
  if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
    return '"' + str.replace(/"/g, '""') + '"';
  }

  return str;
}


/**
 * Convert an array of objects to a CSV string.
 *
 * @param rows    - Array of objects to export. All objects should have the same keys.
 * @param columns - Column definitions: { key: keyof T, header: string }
 * @returns       - CSV string with headers on the first line.
 */
export function objectsToCsv<T extends Record<string, unknown>>(
  rows:    T[],
  columns: Array<{ key: keyof T; header: string }>,
): string {
  if (rows.length === 0) return '';

  // Build header row
  const headerRow = columns.map(col => escapeCsvCell(col.header)).join(',');

  // Build data rows
  const dataRows = rows.map(row =>
    columns.map(col => escapeCsvCell(row[col.key])).join(',')
  );

  // Join all rows with CRLF line endings (RFC 4180 standard)
  return [headerRow, ...dataRows].join('\r\n');
}


/**
 * Trigger a browser download of a CSV file.
 *
 * @param csvString - The CSV content as a string.
 * @param filename  - The suggested filename for the download dialog.
 */
export function downloadCsv(csvString: string, filename: string): void {
  // Create a Blob with the CSV data
  // 'text/csv;charset=utf-8;' tells the browser this is a CSV file
  const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });

  // Create an object URL — a temporary URL pointing to the Blob in memory
  const url = URL.createObjectURL(blob);

  // Create a temporary <a> element (not added to the DOM visually)
  const link = document.createElement('a');
  link.href     = url;
  link.download = filename;  // the `download` attribute sets the filename

  // Temporarily add to DOM, click, and remove
  // This is required for Firefox — it won't trigger the download otherwise
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Release the object URL to free memory
  // Without this, the Blob stays in memory until the page is closed
  URL.revokeObjectURL(url);
}


/**
 * Export a table of objects as a downloaded CSV file.
 *
 * Convenience wrapper that combines objectsToCsv + downloadCsv.
 *
 * @param rows     - Data rows to export.
 * @param columns  - Column definitions.
 * @param filename - Download filename (e.g., 'escalated_accounts_2024-01-15.csv')
 */
export function exportTableToCsv<T extends Record<string, unknown>>(
  rows:     T[],
  columns:  Array<{ key: keyof T; header: string }>,
  filename: string,
): void {
  const csv = objectsToCsv(rows, columns);
  downloadCsv(csv, filename);
}

/**
 * frontend/src/pages/NotFoundPage.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * 404 Not Found page — displayed when the user navigates to an unknown route.
 *
 * Why a dedicated 404 page?
 *   React Router v6 won't show any content for unmatched routes unless we
 *   explicitly add a catch-all route (path="*") with a component. Without it,
 *   the user sees a blank page with no explanation.
 *
 *   A good 404 page:
 *   1. Tells the user what happened (the URL doesn't exist)
 *   2. Doesn't leave them stranded (provides navigation options)
 *   3. Is clearly distinct from a loading state or error state
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    // Full-height centered layout — this page takes the entire viewport
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="text-center max-w-md">

        {/* Large 404 display — visually dominant, immediately communicates the error */}
        <p className="text-8xl font-bold text-gray-700 mb-4">404</p>

        {/* Human-readable explanation */}
        <h1 className="text-2xl font-semibold text-white mb-2">
          Page not found
        </h1>

        <p className="text-gray-400 mb-8">
          The page you're looking for doesn't exist, or the account ID in the
          URL is invalid. Check the URL and try again.
        </p>

        {/* Navigation options — don't leave the user stranded */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            to="/queue"
            className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg
                       font-medium transition-colors duration-150"
          >
            Go to Alert Queue
          </Link>

          <Link
            to="/analytics"
            className="px-6 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg
                       font-medium transition-colors duration-150"
          >
            View Analytics
          </Link>
        </div>

      </div>
    </div>
  );
}

/**
 * frontend/tailwind.config.js
 * Tailwind CSS configuration for the AML Detection dashboard.
 *
 * Custom extensions:
 *   - colors.risk.*: semantic risk-tier colours matching backend scoring_config.py
 *   - animation.fade-in: subtle entrance animation for cards and modals
 *   - fontFamily.mono: preferred monospace fonts for account IDs and scores
 * @type {import('tailwindcss').Config}
 */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Semantic risk tier colours — match TIER_THRESHOLDS in scoring_config.py
        risk: {
          critical: '#ef4444',  // red-500:    score >= 90
          high:     '#f97316',  // orange-500: score >= 70
          medium:   '#eab308',  // yellow-500: score >= 40
          low:      '#22c55e',  // green-500:  score < 40
        },
      },
      animation: {
        'pulse-fast': 'pulse 0.8s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in':    'fadeIn 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}

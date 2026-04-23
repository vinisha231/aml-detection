/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Custom risk tier colors used throughout the dashboard
        critical: '#dc2626',   // red-600   — score 75-100
        high:     '#ea580c',   // orange-600 — score 50-74
        medium:   '#d97706',   // amber-600  — score 25-49
        low:      '#16a34a',   // green-600  — score 0-24
      },
    },
  },
  plugins: [],
}

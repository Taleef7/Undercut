/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0a0a0a',
        card: '#141414',
        accent: '#e10600',
        gold: '#ffd700',
        strong: '#22c55e',
        inspired: '#14b8a6',
        risky: '#f59e0b',
        poor: '#ef4444',
        offwall: '#dc2626',
        muted: '#9ca3af',
        border: '#2e303a',
      },
    },
  },
  plugins: [],
};

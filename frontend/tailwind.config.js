/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#090d16",
        surface: "#111827",
        "surface-border": "#1f2937",
        primary: {
          50: "#eff6ff",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
        },
        accent: {
          emerald: "#10b981",
          amber: "#f59e0b",
          rose: "#f43f5e",
        }
      },
    },
  },
  plugins: [],
}

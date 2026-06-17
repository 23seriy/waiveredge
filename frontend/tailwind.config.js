/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0f1115",
        card: "#181b22",
        line: "#262a33",
        muted: "#9aa0aa",
        pos: "#3fb950",
        neg: "#f85149",
        accent: "#f0883e",
        surface: "#1e2128",
      },
    },
  },
  plugins: [],
}


/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#121820",
          900: "#1b2430",
          700: "#3d4a5c",
          500: "#66758a",
          300: "#c5c0b6",
        },
        paper: "#f4f0e7",
        card: "#fffcf7",
        line: "#e3dacb",
        pine: {
          50: "#eef6f5",
          600: "#1f6f68",
          700: "#185e58",
          800: "#134843",
          900: "#123f3b",
        },
        clay: "#b5682d",
        danger: "#9d2c2c",
      },
      fontFamily: {
        sans: ["Outfit", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["Source Serif 4", "ui-serif", "Georgia", "serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(18, 24, 32, 0.06), 0 12px 32px rgba(18, 24, 32, 0.04)",
      },
    },
  },
  plugins: [],
};

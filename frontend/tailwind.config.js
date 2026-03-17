/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        mystery: {
          900: "#1a0a2e",
          800: "#2d1b4e",
          700: "#462d6e",
          600: "#5e3f8e",
          500: "#7b52ae",
          400: "#9b7bc5",
          300: "#bba4dc",
          200: "#dcccf0",
          100: "#f0e8fa",
        },
      },
    },
  },
  plugins: [],
};

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
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "pulse-glow": {
          "0%, 100%": { textShadow: "0 0 10px rgba(220, 38, 38, 0.5)" },
          "50%": { textShadow: "0 0 30px rgba(220, 38, 38, 0.9)" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 1s ease-out forwards",
        "fade-in": "fade-in 1s ease-out forwards",
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

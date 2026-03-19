/** @type {import('tailwindcss').Config} */
export default {
  content: ["./*.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        mystery: {
          900: "rgb(var(--c-900) / <alpha-value>)",
          800: "rgb(var(--c-800) / <alpha-value>)",
          700: "rgb(var(--c-700) / <alpha-value>)",
          600: "rgb(var(--c-600) / <alpha-value>)",
          500: "rgb(var(--c-500) / <alpha-value>)",
          400: "rgb(var(--c-400) / <alpha-value>)",
          300: "rgb(var(--c-300) / <alpha-value>)",
          200: "rgb(var(--c-200) / <alpha-value>)",
          100: "rgb(var(--c-100) / <alpha-value>)",
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

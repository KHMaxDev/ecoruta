/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ecoruta: {
          green: "#0f766e",
          amber: "#d97706",
          ink: "#111827"
        }
      }
    }
  },
  plugins: []
};

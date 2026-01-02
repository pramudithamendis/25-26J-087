/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    // This tells Tailwind to look in all files under the 'src' folder
    // that have a .js, .ts, .jsx, or .tsx extension.
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
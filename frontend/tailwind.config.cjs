/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          600: '#1a1a8c',
          700: '#15157a',
          800: '#101068',
          900: '#0b0b55',
        },
      },
    },
  },
  plugins: [],
}


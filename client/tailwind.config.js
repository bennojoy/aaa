/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./App.tsx", "./src/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        primary: '#40E0D0',
        secondary: '#5856D6',
        background: '#FFFFFF',
        foreground: '#000000',
        grey: {
          0: '#393e42',
          1: '#43484d',
          2: '#5e6977',
          3: '#86939e',
          4: '#bdc6cf',
          5: '#e1e8ee',
        },
        success: '#4CD964',
        error: '#FF3B30',
        warning: '#FFCC00',
        disabled: '#cccccc',
      },
      fontFamily: {
        sans: ['System'],
      },
    },
  },
  plugins: [],
}; 
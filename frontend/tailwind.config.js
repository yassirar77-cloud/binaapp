/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
          950: '#082f49',
        },
        brand: {
          50: '#EFEDFF',
          100: '#DCD7FF',
          200: '#BAB0FF',
          300: '#8F80FF',
          400: '#6B5CFF',
          500: '#4F3DFF',
          600: '#3D2BE0',
          700: '#2A1FB8',
          800: '#1C1580',
          900: '#120D55',
        },
        ink: {
          '000': '#FFFFFF',
          '050': '#F7F7FA',
          100: '#EEEEF3',
          200: '#DEDEE6',
          300: '#B8B8C4',
          400: '#86869A',
          500: '#5A5A6E',
          600: '#3A3A4A',
          700: '#232334',
          800: '#161623',
          900: '#0B0B15',
          950: '#05050C',
        },
        volt: {
          100: '#F0FFC4',
          300: '#DDFF7A',
          400: '#C7FF3D',
          500: '#A8E81C',
          600: '#7FB500',
        },
        ok: { 400: '#22C08F', 500: '#0F9D6B' },
        warn: { 400: '#FFB020', 500: '#E08800' },
        err: { 400: '#FF5A5F', 500: '#E03A3F' },
        whatsapp: '#25D366',
      },
      fontFamily: {
        geist: ['Geist', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        'geist-mono': ['Geist Mono', 'JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'bounce-slow': 'bounce 2s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}

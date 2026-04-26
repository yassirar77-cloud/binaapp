import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
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
          // Legacy aliases — used by existing admin pages.
          orange: '#ea580c',
          'orange-light': '#f97316',
          'orange-dark': '#c2410c',
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
      },
      fontFamily: {
        sans: ['Geist', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        geist: ['Geist', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        'geist-mono': ['Geist Mono', 'JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(11,11,21,0.06), 0 4px 12px rgba(11,11,21,0.04)',
        card: '0 1px 3px rgba(11,11,21,0.08), 0 8px 24px rgba(11,11,21,0.06)',
        lift: '0 12px 32px rgba(11,11,21,0.12)',
        glow: '0 0 0 4px rgba(79,61,255,0.18)',
      },
      borderRadius: {
        xl2: '1.25rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'scale-in': 'scaleIn 0.18s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(12px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.96)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}

export default config

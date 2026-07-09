/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        board: {
          bg: '#0f172a',
          col: '#1e293b',
          colborder: '#334155',
          header: '#0ea5e9',
        },
        card: {
          blue: { DEFAULT: '#1d4ed8', hover: '#1e40af', border: '#3b82f6' },
          red: { DEFAULT: '#b91c1c', hover: '#991b1b', border: '#ef4444' },
          yellow: { DEFAULT: '#854d0e', hover: '#713f12', border: '#eab308' },
          gray: { DEFAULT: '#374151', hover: '#1f2937', border: '#6b7280' },
          orange: { DEFAULT: '#9a3412', hover: '#7c2d12', border: '#f97316' },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Sora', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-soft': 'bounceSoft 1s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideUp: { '0%': { opacity: '0', transform: 'translateY(20px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        bounceSoft: { '0%, 100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-4px)' } },
      },
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'brand-indigo': '#1E1B4B',
        'brand-amber': '#F59E0B',
        'brand-slate': '#64748B',
        canvas: '#F7F8FC',
        ink: '#17162F',
        'kairos-bg': 'var(--kairos-bg)',
        'kairos-surface': 'var(--kairos-surface)',
        'kairos-text': 'var(--kairos-text)',
        'kairos-muted': 'var(--kairos-muted)',
        'kairos-border': 'var(--kairos-border)',
        'kairos-success': 'var(--kairos-success)',
        'kairos-warning': 'var(--kairos-warning)',
        'kairos-danger': 'var(--kairos-danger)',
        'kairos-info': 'var(--kairos-info)',
        'electric-violet': '#7C6CFF',
      },
      fontFamily: {
        sans: ['Inter', 'Sora', 'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
      },
      boxShadow: {
        soft: '0 1px 2px rgba(30, 27, 75, .03), 0 10px 30px rgba(30, 27, 75, .045)',
        lift: '0 20px 60px rgba(30, 27, 75, .13)',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      keyframes: {
        'fade-up': { '0%': { opacity: '0', transform: 'translateY(8px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        'pulse-soft': { '0%, 100%': { opacity: '1' }, '50%': { opacity: '.45' } },
      },
      animation: {
        'fade-up': 'fade-up .35s ease-out both',
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};

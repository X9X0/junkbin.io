/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Cyberpunk color palette
        cyber: {
          black: '#0a0a0f',
          darker: '#0d0d14',
          dark: '#12121a',
          gray: '#1a1a24',
          light: '#2a2a3a',
          // Neon accents
          pink: '#ff2a6d',
          cyan: '#05d9e8',
          yellow: '#f9f002',
          purple: '#d300c5',
          blue: '#0066ff',
          green: '#39ff14',
          orange: '#ff6b35',
          red: '#ff0055',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        display: ['Orbitron', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'neon-cyan': '0 0 5px #05d9e8, 0 0 20px rgba(5, 217, 232, 0.3)',
        'neon-pink': '0 0 5px #ff2a6d, 0 0 20px rgba(255, 42, 109, 0.3)',
        'neon-green': '0 0 5px #39ff14, 0 0 20px rgba(57, 255, 20, 0.3)',
        'neon-yellow': '0 0 5px #f9f002, 0 0 20px rgba(249, 240, 2, 0.3)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'scan': 'scan 8s linear infinite',
        'flicker': 'flicker 0.15s infinite',
        'yellow-pulse': 'yellow-pulse 1.4s ease-in-out infinite',
      },
      keyframes: {
        'yellow-pulse': {
          '0%, 100%': { opacity: '1', filter: 'brightness(1) drop-shadow(0 0 6px #f9f002)' },
          '50%': { opacity: '0.55', filter: 'brightness(1.6) drop-shadow(0 0 14px #f9f002)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px currentColor, 0 0 10px currentColor' },
          '100%': { boxShadow: '0 0 10px currentColor, 0 0 20px currentColor, 0 0 30px currentColor' },
        },
        scan: {
          '0%': { backgroundPosition: '0% 0%' },
          '100%': { backgroundPosition: '0% 100%' },
        },
        flicker: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.8 },
        },
      },
      backgroundImage: {
        'grid-pattern': 'linear-gradient(rgba(5, 217, 232, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(5, 217, 232, 0.03) 1px, transparent 1px)',
        'scanlines': 'repeating-linear-gradient(0deg, rgba(0,0,0,0.1), rgba(0,0,0,0.1) 1px, transparent 1px, transparent 2px)',
      },
    },
  },
  plugins: [],
}

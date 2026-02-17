/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0e131f',
        slate: '#1f2d3d',
        teal: '#1f8a8a',
        mint: '#8dd8c7',
        sand: '#f2e8cf',
        ember: '#e07a5f'
      },
      boxShadow: {
        panel: '0 10px 30px rgba(6, 19, 37, 0.2)'
      },
      backgroundImage: {
        halo: 'radial-gradient(circle at 20% 20%, rgba(141,216,199,0.24), transparent 42%), radial-gradient(circle at 80% 10%, rgba(31,138,138,0.18), transparent 38%), linear-gradient(140deg, #0b1320, #132032 45%, #0c1a28)'
      }
    }
  },
  plugins: []
};

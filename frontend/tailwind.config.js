/** @type {import('tailwindcss').Config} */
// Colours map to the OrgDesign Playbook tokens in src/index.css.
// `primary` is the Playbook red so existing primary-* classes pick up the accent.
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: '#FAF7F3',
        ink: '#1C1F24',
        secondary: '#575C63',
        faint: '#8A8F96',
        hairline: '#E7E0D8',
        wash: '#F6F1EA',
        track: '#EFE9E1',
        placeholder: '#D8CFC2',
        score: {
          green: '#257A55',
          amber: '#B97F24',
          red: '#B02E2E',
        },
        quad: {
          structure: '#C41E3A',
          people: '#4A5568',
          process: '#2D3748',
          mindset: '#9C6B72',
        },
        primary: {
          50: '#FBEEF0',
          100: '#F6DADF',
          200: '#EDB4BE',
          300: '#E08A99',
          400: '#D25C71',
          500: '#C93A52',
          600: '#C41E3A',
          700: '#9D182E',
          800: '#7A1324',
          900: '#560D19',
        },
      },
      fontFamily: {
        display: ['"Playfair Display"', 'Georgia', 'serif'],
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '2px',
      },
    },
  },
  plugins: [],
}

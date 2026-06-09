const one = require("../docs/archive/design-export/tailwind.tokens.js");

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      ...one.extend,
      gridTemplateColumns: {
        "case-open": "1fr 2fr 1fr",
        "case-closed": "1fr 2.2fr",
      },
    },
  },
  plugins: [],
};

/**
 * ÁSZF Q&A Copilot — One Magyarország design tokens for Tailwind.
 * Merge into your tailwind.config.js `theme.extend`.
 * NOTE: `turq` (#16C7C0) approximates the One brand turquoise — swap for
 * the official hex when available.
 *
 * Example:
 *   const one = require("./docs/design-export/tailwind.tokens.js");
 *   module.exports = { theme: { extend: one.extend } };
 */
module.exports = {
  extend: {
    colors: {
      one: {
        turq: "#16C7C0",
        "turq-d": "#0FA39D",
        "turq-l": "#E3FAF8",
        black: "#0E1212",
        ink: "#16201F",
        grey: "#6B7A79",
        line: "#E2EAE9",
        canvas: "#F7FAF9",
        surface: "#FFFFFF",
      },
      status: {
        "urgent-fg": "#B42318", "urgent-bg": "#FDE2E1",
        "esc-fg": "#B96A00", "esc-bg": "#FFF0DB",
        "conf-fg": "#8A6D00", "conf-bg": "#FEF7D6",
      },
      kpi: { ok: "#22A06B", warn: "#E0A400", bad: "#D64545" },
      highlight: "#FFF3B0",
    },
    fontFamily: {
      sans: ['"Segoe UI"', "system-ui", "-apple-system", "Roboto", "Arial", "sans-serif"],
    },
    borderRadius: {
      one: "12px",      // cards
      "one-lg": "14px", // shell / panels
      pill: "20px",     // buttons, badges
    },
    boxShadow: {
      card: "0 1px 2px rgba(14,18,18,0.04)",
    },
    spacing: {
      rail: "70px",     // icon nav rail
      header: "52px",   // top header
    },
  },
};

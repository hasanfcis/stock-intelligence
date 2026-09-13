import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#14161A",
        panel: "#1B1E24",
        border: "#2A2E37",
        ink: "#E8E6E1",
        muted: "#8B909C",
        amber: "#C9973C",
        gain: "#3FB68C",
        loss: "#E0645A",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;

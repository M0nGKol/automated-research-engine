import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Discord-inspired dark theme
        background: {
          primary: "#1e1f22",
          secondary: "#2b2d31",
          tertiary: "#313338",
          modifier: "#4e5058",
        },
        text: {
          normal: "#dbdee1",
          muted: "#949ba4",
          link: "#00a8fc",
        },
        accent: {
          primary: "#5865f2",
          hover: "#4752c4",
          success: "#23a55a",
          warning: "#f0b132",
          danger: "#da373c",
        },
        border: {
          subtle: "#3f4147",
          strong: "#4e5058",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "slide-up": "slideUp 0.3s ease-out",
        "fade-in": "fadeIn 0.2s ease-out",
      },
      keyframes: {
        slideUp: {
          "0%": { transform: "translateY(10px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;


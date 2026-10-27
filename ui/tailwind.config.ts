import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#e8f3f6",
        muted: "#86a0ab",
        panel: "#0d1a20",
        line: "#1f3540",
        teal: "#2dd4bf",
        blood: "#f87171",
        lung: "#60a5fa",
        amber: "#f5b942",
      },
      fontFamily: {
        sans: ['"Segoe UI"', "system-ui", "sans-serif"],
        mono: ['"Cascadia Mono"', "Consolas", "monospace"],
      },
      keyframes: {
        breathe: {
          "0%,100%": { transform: "scale(1)", opacity: "0.75" },
          "50%": { transform: "scale(1.06)", opacity: "1" },
        },
        beat: {
          "0%,100%": { transform: "scale(1)" },
          "12%": { transform: "scale(1.11)" },
          "24%": { transform: "scale(1)" },
          "36%": { transform: "scale(1.06)" },
          "48%": { transform: "scale(1)" },
        },
        flow: {
          from: { backgroundPosition: "0% 50%" },
          to: { backgroundPosition: "200% 50%" },
        },
        rise: {
          from: { opacity: "0", transform: "translateY(14px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        breathe: "breathe 6s ease-in-out infinite",
        beat: "beat 1.1s ease-in-out infinite",
        flow: "flow 3s linear infinite",
        rise: "rise .6s cubic-bezier(.2,.8,.2,1) both",
      },
    },
  },
  plugins: [],
};

export default config;

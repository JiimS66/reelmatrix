import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#10211b",
        black: "#0c0d0a",
        canvas: "#f4f6ef",
        moss: "#1f6f52",
        forest: "#3f6e1f",
        lime: "#d7f075",
        coral: "#ff7657",
      },
      fontFamily: {
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "Liberation Mono",
          "monospace",
        ],
      },
      boxShadow: {
        card: "0 24px 70px -35px rgba(16, 33, 27, 0.35)",
        soft: "0 1px 2px rgba(16, 33, 27, 0.06), 0 8px 24px -16px rgba(16, 33, 27, 0.25)",
      },
    },
  },
  plugins: [],
};

export default config;

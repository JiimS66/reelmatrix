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
        canvas: "#f4f6ef",
        moss: "#1f6f52",
        lime: "#d7f075",
        coral: "#ff7657",
      },
      boxShadow: {
        card: "0 24px 70px -35px rgba(16, 33, 27, 0.35)",
      },
    },
  },
  plugins: [],
};

export default config;

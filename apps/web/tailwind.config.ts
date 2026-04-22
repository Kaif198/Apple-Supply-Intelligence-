import type { Config } from "tailwindcss";

/**
 * Tailwind configuration for ASCIIP — Apple Pro dark system.
 *
 * The visual language follows apple.com/pro: generous whitespace,
 * display-size sans typography (Inter as SF Pro Display substitute),
 * hairline borders, a restrained monochrome palette with a single
 * interactive accent blue, and subtle spring easing on interactions.
 *
 * Every color is a CSS custom property in `src/app/globals.css` so the
 * palette can flip with `data-theme` without a rebuild.
 */
const config: Config = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: [
    "./src/app/**/*.{ts,tsx,mdx}",
    "./src/components/**/*.{ts,tsx,mdx}",
    "./src/lib/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: {
        DEFAULT: "1.25rem",
        md: "2rem",
        lg: "3rem",
      },
      screens: {
        sm: "640px",
        md: "768px",
        lg: "1024px",
        xl: "1280px",
        "2xl": "1440px",
      },
    },
    extend: {
      colors: {
        bg: {
          canvas: "hsl(var(--bg-canvas) / <alpha-value>)",
          panel: "hsl(var(--bg-panel) / <alpha-value>)",
          raised: "hsl(var(--bg-raised) / <alpha-value>)",
          inset: "hsl(var(--bg-inset) / <alpha-value>)",
          overlay: "hsl(var(--bg-overlay) / <alpha-value>)",
          glass: "hsl(var(--bg-glass) / <alpha-value>)",
        },
        fg: {
          DEFAULT: "hsl(var(--fg-default) / <alpha-value>)",
          muted: "hsl(var(--fg-muted) / <alpha-value>)",
          subtle: "hsl(var(--fg-subtle) / <alpha-value>)",
          inverted: "hsl(var(--fg-inverted) / <alpha-value>)",
        },
        border: {
          DEFAULT: "hsl(var(--border-default) / <alpha-value>)",
          subtle: "hsl(var(--border-subtle) / <alpha-value>)",
          strong: "hsl(var(--border-strong) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "hsl(var(--accent) / <alpha-value>)",
          foreground: "hsl(var(--accent-foreground) / <alpha-value>)",
          muted: "hsl(var(--accent-muted) / <alpha-value>)",
        },
        signal: {
          pos: "hsl(var(--signal-pos) / <alpha-value>)",
          neg: "hsl(var(--signal-neg) / <alpha-value>)",
          warn: "hsl(var(--signal-warn) / <alpha-value>)",
          info: "hsl(var(--signal-info) / <alpha-value>)",
        },
        severity: {
          low: "hsl(var(--severity-low) / <alpha-value>)",
          medium: "hsl(var(--severity-medium) / <alpha-value>)",
          high: "hsl(var(--severity-high) / <alpha-value>)",
          critical: "hsl(var(--severity-critical) / <alpha-value>)",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        display: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      fontSize: {
        // Apple-scale type ramp — from micro labels up to hero display.
        xxs: ["10px", { lineHeight: "14px", letterSpacing: "0.02em" }],
        xs: ["12px", { lineHeight: "18px", letterSpacing: "0.01em" }],
        sm: ["13px", { lineHeight: "20px" }],
        base: ["15px", { lineHeight: "24px" }],
        md: ["17px", { lineHeight: "26px" }],
        lg: ["19px", { lineHeight: "28px", letterSpacing: "-0.01em" }],
        xl: ["24px", { lineHeight: "32px", letterSpacing: "-0.015em" }],
        "2xl": ["32px", { lineHeight: "38px", letterSpacing: "-0.02em" }],
        "3xl": ["40px", { lineHeight: "46px", letterSpacing: "-0.025em" }],
        "4xl": ["52px", { lineHeight: "56px", letterSpacing: "-0.03em" }],
        "5xl": ["68px", { lineHeight: "72px", letterSpacing: "-0.035em" }],
        "6xl": ["88px", { lineHeight: "92px", letterSpacing: "-0.04em" }],
        "7xl": ["112px", { lineHeight: "112px", letterSpacing: "-0.045em" }],
      },
      spacing: {
        0.75: "3px",
        1.25: "5px",
        1.5: "6px",
        2.25: "9px",
        18: "4.5rem",
        22: "5.5rem",
        30: "7.5rem",
        "cell-x": "10px",
        "cell-y": "6px",
      },
      borderRadius: {
        xs: "2px",
        sm: "4px",
        md: "8px",
        lg: "12px",
        xl: "16px",
        "2xl": "20px",
        "3xl": "28px",
      },
      boxShadow: {
        panel: "0 1px 0 hsl(var(--border-subtle) / 1)",
        raised:
          "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 10px 30px -10px rgba(0,0,0,0.5)",
        elevated:
          "0 1px 0 0 rgba(255,255,255,0.05) inset, 0 30px 60px -30px rgba(0,0,0,0.7)",
        focus: "0 0 0 3px hsl(var(--accent) / 0.4)",
      },
      transitionTimingFunction: {
        spring: "cubic-bezier(0.22, 1, 0.36, 1)",
        emph: "cubic-bezier(0.16, 1, 0.3, 1)",
      },
      transitionDuration: {
        400: "400ms",
        600: "600ms",
        800: "800ms",
      },
      keyframes: {
        pulseSubtle: {
          "0%, 100%": { opacity: "0.45" },
          "50%": { opacity: "1" },
        },
        fadeIn: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        fadeInSlow: {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        glow: {
          "0%, 100%": { opacity: "0.55" },
          "50%": { opacity: "1" },
        },
        drift: {
          "0%": { transform: "translateY(0)" },
          "100%": { transform: "translateY(-4px)" },
        },
      },
      animation: {
        "pulse-subtle": "pulseSubtle 2.4s ease-in-out infinite",
        "fade-in": "fadeIn 520ms cubic-bezier(0.22,1,0.36,1) both",
        "fade-in-slow":
          "fadeInSlow 820ms cubic-bezier(0.22,1,0.36,1) both",
        glow: "glow 5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;

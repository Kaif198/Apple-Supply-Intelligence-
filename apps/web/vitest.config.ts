import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

/**
 * Vitest config for the web app.
 *
 * Mirrors the Next.js path alias (`@/*` -> `src/*`) so tests can import
 * modules using the same shorthand as production code. Uses jsdom for
 * React Testing Library compatibility and loads a setup file that wires
 * @testing-library/jest-dom matchers globally.
 */
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["node_modules", ".next", "e2e", "dist"],
    passWithNoTests: false,
    coverage: {
      reporter: ["text", "html", "lcov"],
      include: ["src/lib/**/*.ts", "src/components/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.d.ts",
        "src/**/*.test.*",
        "src/**/*.spec.*",
        "src/test/**",
      ],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});

import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration.
 *
 * In CI the `e2e.yml` workflow starts both services manually and sets
 * `BASE_URL=http://127.0.0.1:3000`; locally developers can run
 * `pnpm run e2e` after `make up` (docker-compose) or after `pnpm dev`.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.BASE_URL ?? "http://127.0.0.1:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    viewport: { width: 1440, height: 900 },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});

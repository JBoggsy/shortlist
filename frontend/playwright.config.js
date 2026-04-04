import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E test config for Shortlist.
 *
 * Assumes both servers are already running:
 *   - Flask backend on http://localhost:5000
 *   - Vite frontend on http://localhost:3000
 *
 * Run:  npm run test:e2e
 * Run single:  npx playwright test tests/e2e/01-first-launch.spec.js
 * UI mode:  npx playwright test --ui
 */
export default defineConfig({
  testDir: "./tests/e2e",
  /* Increase default timeout — LLM responses can be slow */
  timeout: 120_000,
  expect: {
    timeout: 15_000,
  },
  /* Run tests in order (scenarios build on each other) */
  fullyParallel: false,
  workers: 1,
  /* Retry once on failure */
  retries: 1,
  /* Reporter */
  reporter: [["html", { open: "never" }], ["list"]],
  /* Shared settings for all tests */
  use: {
    baseURL: "http://localhost:3000",
    /* Collect trace on first retry for debugging */
    trace: "on-first-retry",
    /* Screenshot on failure */
    screenshot: "only-on-failure",
    /* Video on first retry */
    video: "on-first-retry",
    /* Reasonable viewport */
    viewport: { width: 1440, height: 900 },
    /* Don't wait forever for navigation */
    navigationTimeout: 15_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  /* Output directory for test artifacts */
  outputDir: "./tests/e2e/test-results",
  /* Do NOT auto-start servers — they must be running already.
   * Use `./start.sh` before running tests. */
});

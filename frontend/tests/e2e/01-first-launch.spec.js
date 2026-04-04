/**
 * Scenario 1: First Launch & Health Check
 *
 * Tests clean-state detection, health endpoint, and setup wizard auto-trigger.
 * Prereq: user_data/ wiped (no config.json, no app.db, no user_profile.md)
 */
import { test, expect, TEST_CONFIG } from "./fixtures.js";

test.describe("Scenario 1: First Launch & Health Check", () => {
  // Clean slate: delete any leftover jobs and conversations from previous runs
  test.beforeAll(async ({ request }) => {
    const jobsResp = await request.get(`${TEST_CONFIG.backendUrl}/api/jobs`);
    if (jobsResp.ok()) {
      const jobs = await jobsResp.json();
      for (const job of jobs) {
        await request.delete(`${TEST_CONFIG.backendUrl}/api/jobs/${job.id}`);
      }
    }
    const convResp = await request.get(`${TEST_CONFIG.backendUrl}/api/chat/conversations`);
    if (convResp.ok()) {
      const convs = await convResp.json();
      for (const c of convs) {
        await request.delete(`${TEST_CONFIG.backendUrl}/api/chat/conversations/${c.id}`);
      }
    }
  });
  test("health endpoint returns 503 when LLM not configured", async ({
    app,
  }) => {
    const resp = await app.page.request.get(
      `${TEST_CONFIG.backendUrl}/api/health`
    );
    expect(resp.status()).toBe(503);
  });

  test("home page shows warning banner and setup wizard", async ({
    app,
    page,
  }) => {
    await app.goto("/", { dismissWizard: false });

    // Warning banner about unconfigured AI
    await expect(
      page.getByText(/not configured|set up|configure/i).first()
    ).toBeVisible();

    // Setup wizard should auto-open
    await expect(
      page.getByText(/welcome/i).first()
    ).toBeVisible({ timeout: 5000 });
  });

  test("navigation bar is visible behind wizard", async ({ app, page }) => {
    await app.goto("/", { dismissWizard: false });
    await expect(page.getByRole("link", { name: /home/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /jobs/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /settings/i })).toBeVisible();
  });

  test("jobs page shows empty state", async ({ app, page }) => {
    await app.goto("/jobs");
    await expect(
      page.getByText(/no.*applications|no.*jobs|get started/i).first()
    ).toBeVisible();
  });

  test("settings page loads in unconfigured state", async ({ app, page }) => {
    await app.goto("/settings");
    await expect(page.getByText(/provider|llm/i).first()).toBeVisible();
  });
});

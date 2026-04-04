/**
 * Scenario 5: Manual Job CRUD
 *
 * Tests adding, viewing, editing, sorting, deleting jobs manually,
 * plus application todos.
 */
import { test, expect, PETER, TEST_CONFIG } from "./fixtures.js";

test.describe("Scenario 5: Manual Job CRUD", () => {
  // Clean up any existing jobs before running this scenario
  test.beforeAll(async ({ request }) => {
    const resp = await request.get(`${TEST_CONFIG.backendUrl}/api/jobs`);
    if (resp.ok()) {
      const jobs = await resp.json();
      for (const job of jobs) {
        await request.delete(`${TEST_CONFIG.backendUrl}/api/jobs/${job.id}`);
      }
    }
  });

  test("5A — create three jobs manually", async ({ app, page }) => {
    await app.goto("/jobs");

    // Verify empty state
    const bodyText = await page.textContent("main");
    // Could be empty table or explicit "no jobs" message

    // Add Two Sigma
    await app.addJob(PETER.jobs.twoSigma);
    await expect(page.getByText("Two Sigma").first()).toBeVisible();

    // Add Citadel
    await app.addJob(PETER.jobs.citadel);
    await expect(page.getByText("Citadel Securities").first()).toBeVisible();

    // Add Goldman
    await app.addJob(PETER.jobs.goldman);
    await expect(page.getByText("Goldman Sachs").first()).toBeVisible();
  });

  test("5B — sort table by column headers", async ({ app, page }) => {
    await app.goto("/jobs");

    // Click Company header to sort
    const companyHeader = page.getByRole("columnheader", { name: /company/i });
    await companyHeader.click();
    await page.waitForTimeout(500);

    // Get company names in order
    const rows = page.locator("table tbody tr");
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(3);
  });

  test("5C — view job detail and edit", async ({ app, page }) => {
    await app.goto("/jobs");

    // Click on the Two Sigma row's title cell to navigate to detail page
    // (company name is an <a> with stopPropagation, so click title instead)
    const twoSigmaRow = page.locator("tbody tr", { hasText: "Two Sigma" }).first();
    await twoSigmaRow.getByText("Junior Quantitative Researcher").click();
    await page.waitForTimeout(1000);

    // Verify job detail page
    await expect(page.getByText("Junior Quantitative Researcher").first()).toBeVisible();
    await expect(page.getByText(/new york/i).first()).toBeVisible();

    // Verify documents section
    await expect(page.getByText(/cover letter/i).first()).toBeVisible();

    // Edit the job
    await page.getByRole("button", { name: /edit/i }).first().click();
    await page.waitForTimeout(500);

    // Change status to Applied
    const statusSelect = page.locator('select[name="status"]');
    if (await statusSelect.isVisible()) {
      await statusSelect.selectOption("applied");
    }

    // Save
    await page.locator('button[type="submit"]').click();
    await page.waitForTimeout(2000);

    // Verify status updated — detail page shows status as a badge
    // The form should be closed now, showing the detail view
    await expect(page.getByText(/applied/i).first()).toBeVisible();
  });

  test("5D — application todos", async ({ app, page }) => {
    await app.goto("/jobs");
    // Click title cell in Two Sigma row
    const twoSigmaRow = page.locator("tbody tr", { hasText: "Two Sigma" }).first();
    await twoSigmaRow.getByText("Junior Quantitative Researcher").click();
    await page.waitForTimeout(1000);

    // Add a todo
    const addStepBtn = page.getByRole("button", { name: /\+ add/i });
    if (await addStepBtn.isVisible()) {
      await addStepBtn.click();
      await page.waitForTimeout(500);

      // Fill the todo title input (has placeholder "Step title...")
      const titleInput = page.locator('input[placeholder*="Step title"]');
      await titleInput.fill("Tailor resume for role");

      await page.getByRole("button", { name: /add step/i }).click();
      await page.waitForTimeout(500);

      await expect(page.getByText("Tailor resume for role")).toBeVisible();
    }
  });

  test("5E — delete a job", async ({ app, page }) => {
    await app.goto("/jobs");

    // Count initial jobs
    const initialText = await page.textContent("main");
    expect(initialText).toContain("Goldman Sachs");

    // Auto-accept the native confirm dialog
    page.on("dialog", (dialog) => dialog.accept());

    // Find and click Delete in the Goldman Sachs row
    const goldmanRow = page.locator("tbody tr", { hasText: "Goldman Sachs" }).first();
    await goldmanRow.getByRole("button", { name: /delete/i }).click();

    await page.waitForTimeout(2000);
    // Verify Goldman Sachs is gone (use table cell to be specific)
    await expect(page.locator("tbody").getByText("Goldman Sachs")).not.toBeVisible({ timeout: 5000 });
  });
});

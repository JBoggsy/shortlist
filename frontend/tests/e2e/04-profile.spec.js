/**
 * Scenario 4: Profile Page & Resume Upload
 *
 * Tests profile viewing, manual editing, and resume upload + parsing.
 *
 * Prereq: Onboarding completed (Scenario 3), profile is populated.
 */
import { test, expect } from "./fixtures.js";

test.describe("Scenario 4: Profile Page", () => {
  test.beforeEach(async ({ app }) => {
    await app.goto("/profile");
  });

  test("4A — profile displays onboarded data", async ({ page }) => {
    // Profile should show Peter's data from onboarding
    const content = await page.textContent("main");
    expect(content).toMatch(/summary|experience|skills/i);
  });

  test("4A — edit and save profile", async ({ page }) => {
    // Click Edit
    await page.getByRole("button", { name: /edit/i }).first().click();

    // Textarea should appear
    const textarea = page.locator("textarea").first();
    await expect(textarea).toBeVisible();

    // Append text
    const current = await textarea.inputValue();
    await textarea.fill(
      current +
        "\n\nTends to over-research companies before applying. Gets stuck in analysis paralysis sometimes."
    );

    // Save
    await page.getByRole("button", { name: /save/i }).first().click();
    await page.waitForTimeout(1000);

    // Verify the new text renders
    await expect(page.getByText(/analysis paralysis/i).first()).toBeVisible();
  });

  test("4A — cancel edit discards changes", async ({ page }) => {
    await page.getByRole("button", { name: /edit/i }).first().click();

    const textarea = page.locator("textarea").first();
    const original = await textarea.inputValue();
    await textarea.fill(original + "\n\nTHIS SHOULD NOT BE SAVED");

    // Cancel
    await page.getByRole("button", { name: /cancel/i }).first().click();
    await page.waitForTimeout(500);

    // Verify the discarded text is not present
    await expect(page.getByText("THIS SHOULD NOT BE SAVED")).not.toBeVisible();
  });
});

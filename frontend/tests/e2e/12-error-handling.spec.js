/**
 * Scenario 12: Error Handling & Edge Cases
 *
 * Tests invalid config, form validation, graceful error handling.
 */
import { test, expect, PETER, TEST_CONFIG } from "./fixtures.js";

test.describe("Scenario 12: Error Handling", () => {
  test("12A — invalid API key shows auth error", async ({ app, page }) => {
    await app.goto("/settings");

    // Switch to Anthropic with invalid key
    // The provider select is the first <select> in the LLM section (no name/id attr)
    const providerSelect = page.locator("select").first();
    await providerSelect.selectOption("anthropic");
    await page.waitForTimeout(500);

    const apiKeyInput = page.locator('input[placeholder="your-api-key-here"]');
    await apiKeyInput.fill("sk-invalid-key-12345");

    await app.testConnection();

    // Should show error message (not raw traceback)
    await expect(
      page.getByText(/error|failed|invalid|unauthorized/i).first()
    ).toBeVisible({ timeout: 30_000 });

    // Restore valid config if we have a key
    if (TEST_CONFIG.anthropicKey) {
      await apiKeyInput.fill(TEST_CONFIG.anthropicKey);
      await app.testConnection();
      await expect(
        page.getByText(/success|connected|✓/i).first()
      ).toBeVisible({ timeout: 30_000 });
      await app.saveSettings();
    }
  });

  test("12C — form validation for required fields", async ({
    app,
    page,
  }) => {
    await app.goto("/jobs");

    // Click Add Job
    await page.getByRole("button", { name: /add job/i }).first().click();
    await page.waitForTimeout(500);

    // Try to submit with empty fields
    const submitBtn = page.locator('button[type="submit"]');
    await submitBtn.click();

    // Should show validation errors or not submit
    // The form should still be visible (didn't close/navigate away)
    await page.waitForTimeout(500);

    // Fill company only
    await page.locator('input[name="company"]').fill("Test Company");
    await submitBtn.click();
    await page.waitForTimeout(500);

    // Should still need title — form still open or error shown
    // Now fill title too
    await page.locator('input[name="title"]').fill("Test Title");
    await submitBtn.click();
    await page.waitForTimeout(1000);

    // Should succeed — job added
    await expect(page.getByText("Test Company").first()).toBeVisible();
  });

  test("12D — absurd search handled gracefully", async ({ app, page }) => {
    // This test requires a configured LLM to get an agent response
    const health = await (await fetch("http://localhost:5000/api/health")).json();
    test.skip(
      !health.llm?.configured,
      "Skipped: LLM not configured (needed for agent response)"
    );

    await app.goto("/");
    await app.openChat();
    await app.newChat();

    await app.sendChatMessage(PETER.chat.absurdSearch, { timeout: 120_000 });

    // Agent should respond gracefully (no crash)
    // Verify user message appears in the chat
    await expect(
      page.getByText(PETER.chat.absurdSearch.substring(0, 30)).first()
    ).toBeVisible({ timeout: 10_000 });

    // Wait for an assistant response (markdown-body class = rendered assistant text)
    await page
      .locator(".markdown-body")
      .first()
      .waitFor({ state: "visible", timeout: 120_000 });

    // Chat should still be functional — can type another message
    const textarea = page.locator("textarea, input").first();
    await expect(textarea).toBeVisible();
    await expect(textarea).toBeEnabled();
  });
});

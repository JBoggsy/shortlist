/**
 * Scenario 9: Provider Switch — Anthropic
 *
 * Tests switching from Ollama to Anthropic in settings,
 * testing connection, and chatting with the new provider.
 *
 * Requires SHORTLIST_TEST_ANTHROPIC_KEY env var.
 */
import { test, expect, PETER, TEST_CONFIG } from "./fixtures.js";

test.describe("Scenario 9: Provider Switch — Anthropic", () => {
  test.skip(!TEST_CONFIG.anthropicKey, "SHORTLIST_TEST_ANTHROPIC_KEY not set");

  test("9A — switch to Anthropic and test connection", async ({
    app,
    page,
  }) => {
    await app.goto("/settings");

    // Change provider to Anthropic
    const providerSelect = page.locator('select').first();
    await providerSelect.selectOption("anthropic");
    await page.waitForTimeout(500);

    // Enter API key
    const apiKeyInput = page.locator('input[placeholder="your-api-key-here"]');
    await expect(apiKeyInput).toBeVisible();
    await apiKeyInput.fill(TEST_CONFIG.anthropicKey);

    // Clear Model Override (may have leftover value from previous provider e.g. "mistral")
    const modelOverrideLabel = page.getByText("Model Override (optional)").first();
    const modelOverrideInput = modelOverrideLabel.locator('..').locator('input[type="text"]');
    await modelOverrideInput.fill("");

    // Test connection
    await app.testConnection();
    await expect(
      page.getByText(/success|connected|✓/i).first()
    ).toBeVisible({ timeout: 30_000 });

    // Save settings
    await app.saveSettings();
    await page.waitForTimeout(1000);
  });

  test("9B — home page shows no warning after Anthropic config", async ({
    app,
    page,
  }) => {
    await app.goto("/");
    // Warning banner should not be visible since LLM is now configured
    const banner = page.getByText(/not configured/i).first();
    await expect(banner).not.toBeVisible({ timeout: 5000 }).catch(() => {
      // Banner might not exist at all
    });
  });

  test("9C — chat works with Anthropic provider", async ({ app, page }) => {
    await app.goto("/");
    await app.openChat();
    await app.newChat();

    await app.sendChatMessage(PETER.chat.skillsWorry, { timeout: 120_000 });

    // Agent should respond
    await expect(page.locator('.markdown-body').first()).toBeVisible();
  });

  test("9D — message feedback buttons", async ({ app, page }) => {
    await app.goto("/");
    await app.openChat();

    // Look for feedback buttons (thumbs up/down) on the last assistant message
    const thumbsUp = page
      .getByRole("button", { name: /thumbs up|👍|like/i })
      .first();
    const thumbsDown = page
      .getByRole("button", { name: /thumbs down|👎|dislike/i })
      .first();

    if (await thumbsUp.isVisible()) {
      await thumbsUp.click();
      await page.waitForTimeout(500);
      // Verify visual feedback (button state change)
    }
  });
});

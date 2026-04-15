/**
 * Scenario 2: Setup Wizard — Ollama Provider
 *
 * Walks through the 5-step setup wizard selecting Ollama,
 * testing connection, entering Tavily key, and launching onboarding.
 *
 * Requires clean state: no config.json, no user_profile.md
 */
import { test, expect, TEST_CONFIG } from "./fixtures.js";

test.describe("Scenario 2: Setup Wizard — Ollama", () => {
  // Cold-starting a large Ollama model can take 90s+, plus wizard steps and onboarding greeting
  test.setTimeout(300_000);

  test("complete setup wizard with Ollama provider", async ({ app, page }) => {
    await app.goto("/", { dismissWizard: false });

    // Step 1 — Welcome: click through
    await expect(page.getByText(/welcome/i).first()).toBeVisible({
      timeout: 10000,
    });
    // "Continue →" button
    await app.wizardNext();

    // Step 2 — Choose Provider
    await expect(page.getByText(/ollama/i).first()).toBeVisible();
    await app.wizardSelectProvider("Ollama");
    await page.waitForTimeout(300);
    await app.wizardNext();

    // Step 3 — API Key / Connection (Ollama needs no key)
    // The auto-detected model (qwen3.5:35b or gemma3:27b) supports tool calling.
    // No manual override needed — just test the connection with the default.
    await expect(
      page.getByRole("button", { name: /test connection/i })
    ).toBeVisible({ timeout: 5000 });

    // If a specific test model is set via env var, override it
    if (TEST_CONFIG.ollamaModel) {
      const advancedToggle = page.getByText(/advanced.*model/i).first();
      await advancedToggle.click();
      await page.waitForTimeout(300);

      const modelInput = page.locator('input').filter({ hasText: '' }).locator('visible=true').last();
      await modelInput.fill(TEST_CONFIG.ollamaModel);
      await page.waitForTimeout(500);

      // Select from dropdown if visible, otherwise click elsewhere to close
      const modelOption = page.locator('li').filter({ hasText: TEST_CONFIG.ollamaModel }).first();
      if (await modelOption.isVisible().catch(() => false)) {
        await modelOption.click();
        await page.waitForTimeout(300);
      } else {
        await page.locator('h2').first().click();
        await page.waitForTimeout(300);
      }
    }

    // Test connection
    await page.getByRole("button", { name: /test connection/i }).click({ force: true });
    // Wait for success (Ollama models may need 90s+ for cold start)
    await expect(
      page.locator("text=/Connected|Success|✓/i").first()
    ).toBeVisible({ timeout: 120_000 });

    await app.wizardNext();

    // Step 4 — Integrations (Tavily, RapidAPI)
    if (TEST_CONFIG.tavilyKey) {
      const tavilyInput = page.locator('input[placeholder="tvly-..."]');
      if (await tavilyInput.isVisible().catch(() => false)) {
        await tavilyInput.fill(TEST_CONFIG.tavilyKey);
      }
    }
    // Button says "Save & Continue →" — wizardNext() matches "continue"
    await app.wizardNext();
    // Wait for config save
    await page.waitForTimeout(2000);

    // Step 5 — Done
    await expect(
      page.getByText(/all set/i).first()
    ).toBeVisible({ timeout: 10000 });

    // Launch onboarding via "Meet Your AI Assistant →"
    const launchBtn = page
      .getByRole("button", {
        name: /meet.*assistant|launch|start|onboarding|get started/i,
      })
      .first();
    await launchBtn.click();

    // Wizard should close and chat/onboarding should start
    await page.waitForTimeout(3000);
    // Onboarding chat panel should be visible with its textarea
    await expect(
      page.locator('textarea[placeholder*="Tell me"]')
    ).toBeVisible({ timeout: 30_000 });

    // Wait for agent greeting (may take a while with Ollama)
    await expect(
      page.locator('.markdown-body').first()
    ).toBeVisible({ timeout: 120_000 });
  });
});

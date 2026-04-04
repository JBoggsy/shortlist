/**
 * Scenario 10: Agent Mode Switch & Advanced Features
 *
 * Tests switching agent designs, orchestrated queries,
 * multi-job comparison, and profile auto-updates.
 */
import { test, expect, PETER } from "./fixtures.js";

test.describe("Scenario 10: Agent Mode Switch", () => {
  test("10A — switch to micro_agents_v1", async ({ app, page }) => {
    await app.goto("/settings");

    // Agent mode uses buttons, not a select
    const orchestratedBtn = page.getByRole("button", { name: "Orchestrated" });
    await orchestratedBtn.click();

    await app.saveSettings();
    await page.waitForTimeout(1000);
  });

  test("10B — orchestrated job search", async ({ app, page }) => {
    await app.goto("/");
    await app.openChat();
    await app.newChat();

    await app.sendChatMessage(PETER.chat.orchestratedSearch, {
      timeout: 300_000, // orchestrated may take longer
    });

    // Agent should provide results
    await page.waitForTimeout(3000);
    await expect(page.locator('.markdown-body').first()).toBeVisible();
  });

  test("10C — multi-job comparison", async ({ app, page }) => {
    await app.goto("/");
    await app.openChat();
    await app.newChat();

    await app.sendChatMessage(PETER.chat.compareJobs, { timeout: 180_000 });

    await page.waitForTimeout(3000);
    const lastMessage = page.locator('.markdown-body').last();
    const text = await lastMessage.textContent();
    // Should mention specific jobs
    expect(text.length).toBeGreaterThan(100);
  });

  test("10D — profile auto-update from chat", async ({ app, page }) => {
    await app.goto("/");
    await app.openChat();
    await app.newChat();

    await app.sendChatMessage(PETER.chat.profileUpdate, { timeout: 180_000 });
    await page.waitForTimeout(3000);

    // Verify profile was updated
    await app.goto("/profile");
    const content = await page.textContent("main");
    // Agent should have added C++ or systematic trading
    expect(content).toMatch(/c\+\+|systematic/i);
  });

  test("10E — switch back to default agent", async ({ app, page }) => {
    await app.goto("/settings");

    // Switch back to Freeform (default) mode
    const freeformBtn = page.getByRole("button", { name: "Freeform" });
    await freeformBtn.click();

    await app.saveSettings();

    // Chat with default agent
    await app.goto("/");
    await app.openChat();
    await app.newChat();

    await app.sendChatMessage(PETER.chat.statusSummary, { timeout: 120_000 });
    await page.waitForTimeout(3000);

    const lastMessage = page.locator('.markdown-body').last();
    const text = await lastMessage.textContent();
    expect(text.length).toBeGreaterThan(50);
  });
});

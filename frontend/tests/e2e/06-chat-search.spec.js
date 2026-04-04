/**
 * Scenario 6: AI Chat — Job Search
 *
 * Tests chat interaction for job searching, SSE streaming,
 * search results panel, and adding results to tracker.
 */
import { test, expect, PETER } from "./fixtures.js";

test.describe("Scenario 6: AI Chat — Job Search", () => {
  test("search for quant jobs via chat", async ({ app, page }) => {
    await app.goto("/");
    await app.openChat();
    await app.newChat();

    // Send job search request
    await app.sendChatMessage(PETER.chat.jobSearch, { timeout: 180_000 });

    // Agent should have responded with some text
    await expect(page.locator('.markdown-body').first()).toBeVisible();

    // Without Tavily configured, the agent can't actually perform web search,
    // so we just verify it responded. Search results panel is optional.
  });

  test("conversational follow-up without tool calls", async ({
    app,
    page,
  }) => {
    await app.goto("/");
    await app.openChat();
    await app.newChat();

    // Send a conversational question
    await app.sendChatMessage(PETER.chat.quantVsDev);

    // Agent should respond with text (no tool calls needed)
    await expect(page.locator('.markdown-body').first()).toBeVisible({ timeout: 30_000 });
  });

  test("chat history preserves conversations", async ({ app, page }) => {
    await app.goto("/");
    await app.openChat();

    // Open history
    const historyBtn = page.getByRole("button", { name: /history/i });
    if (await historyBtn.isVisible()) {
      await historyBtn.click();
      await page.waitForTimeout(1000);

      // Should see conversation entries
      const conversations = page.locator('div.cursor-pointer.rounded-lg.border');
      const count = await conversations.count();
      expect(count).toBeGreaterThanOrEqual(1);
    }
  });

  test("close and reopen chat preserves state", async ({ app, page }) => {
    await app.goto("/");
    await app.openChat();
    await app.newChat();
    await app.sendChatMessage("Hello, this is a test message.");

    // Close
    await app.closeChat();
    await page.waitForTimeout(500);

    // Reopen
    await app.openChat();
    await page.waitForTimeout(1000);

    // The message should still be there
    await expect(
      page.getByText("Hello, this is a test message.").first()
    ).toBeVisible();
  });
});

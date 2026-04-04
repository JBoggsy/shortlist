/**
 * Scenario 11: Navigation & UI Polish
 *
 * Tests nav bar, Help page, Home stats, chat history, toasts, resizing.
 */
import { test, expect } from "./fixtures.js";

test.describe("Scenario 11: Navigation & UI Polish", () => {
  test("nav bar links and active states", async ({ app, page }) => {
    await app.goto("/");

    const pages = [
      { name: /home/i, url: "/" },
      { name: /jobs/i, url: "/jobs" },
      { name: /profile/i, url: "/profile" },
      { name: /settings/i, url: "/settings" },
      { name: /help/i, url: "/help" },
    ];

    for (const p of pages) {
      await page.getByRole("link", { name: p.name }).click();
      await page.waitForTimeout(1000);
      // Verify the page loaded (URL matches)
      expect(page.url()).toContain(p.url === "/" ? "localhost" : p.url);
    }
  });

  test("help page renders all sections", async ({ app, page }) => {
    await app.goto("/help");

    await expect(page.getByText(/getting started/i).first()).toBeVisible();
    await expect(page.getByText(/job tracking/i).first()).toBeVisible();
    await expect(page.getByText(/ai chat/i).first()).toBeVisible();
    await expect(page.getByText(/api key/i).first()).toBeVisible();
    await expect(page.getByText(/troubleshooting/i).first()).toBeVisible();
  });

  test("home page shows job stats", async ({ app, page }) => {
    await app.goto("/");

    // Should show stat cards (Total, Applied, etc.)
    await expect(
      page.getByText(/total|applications/i).first()
    ).toBeVisible();
  });

  test("chat history lists conversations", async ({ app, page }) => {
    await app.goto("/");

    await app.openChat();

    // Verify the History button is present and clickable
    const historyBtn = page.getByRole("button", { name: /history/i });
    await expect(historyBtn).toBeVisible();
    await historyBtn.click();
    await page.waitForTimeout(1000);

    // On clean state, should show "No conversations" message
    // After previous scenarios have run, should show conversation list
    const noConversations = page.getByText(/no conversations/i);
    const hasEmptyState = await noConversations.isVisible().catch(() => false);
    if (!hasEmptyState) {
      // If conversations exist, verify the list is present
      // Conversation items are clickable rounded-lg border divs
      const items = page.locator('div.cursor-pointer.rounded-lg.border');
      const count = await items.count();
      expect(count).toBeGreaterThanOrEqual(1);
    }
    // Either way, the chat panel should remain functional
    await expect(page.getByRole("button", { name: /new chat/i })).toBeVisible();
  });
});

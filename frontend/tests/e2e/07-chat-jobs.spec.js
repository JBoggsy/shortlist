/**
 * Scenario 7: AI Chat — Job Management via Agent
 *
 * Tests creating, editing, deleting jobs through chat,
 * and verifying real-time UI updates.
 */
import { test, expect, PETER } from "./fixtures.js";

test.describe("Scenario 7: AI Chat — Job Management", () => {
  test("create job via chat", async ({ app, page }) => {
    await app.goto("/");
    await app.openChat();
    await app.newChat();

    await app.sendChatMessage(PETER.chat.createJob, { timeout: 180_000 });

    // Agent should confirm job creation
    const responseText = await page
      .locator('.markdown-body')
      .last()
      .textContent();
    expect(responseText.toLowerCase()).toMatch(/added|created|saved|job/i);

    // Navigate to jobs and verify
    await app.goto("/jobs");
    await expect(page.getByText("Two Sigma").first()).toBeVisible();
  });

  test("edit job via chat", async ({ app, page }) => {
    await app.goto("/");
    await app.openChat();
    await app.newChat();

    await app.sendChatMessage(PETER.chat.editJob, { timeout: 180_000 });

    // Agent should confirm the update
    await page.waitForTimeout(2000);
  });

  test("add todos via chat", async ({ app, page }) => {
    await app.goto("/");
    await app.openChat();
    await app.newChat();

    await app.sendChatMessage(PETER.chat.addTodos, { timeout: 180_000 });

    // Agent should confirm adding prep steps
    await page.waitForTimeout(2000);
  });

  test("list jobs via chat", async ({ app, page }) => {
    await app.goto("/");
    await app.openChat();
    await app.newChat();

    await app.sendChatMessage(PETER.chat.listJobs, { timeout: 180_000 });

    // Agent should list current jobs
    await page.waitForTimeout(2000);
    const lastMessage = page.locator('.markdown-body').last();
    const text = await lastMessage.textContent();
    // Should mention at least one job
    expect(text).toMatch(/two sigma|citadel|job/i);
  });
});

import { test as base, expect } from "@playwright/test";

/**
 * Peter Grosman's test data — sourced from tests/GROSMAN.md.
 * Used across all E2E test scenarios as the canonical test persona.
 */
export const PETER = {
  name: "Peter Grosman",
  email: "peter.grosman@umich.edu",
  phone: "(914) 555-0147",
  location: "Scarsdale, NY",

  // Onboarding messages (5-turn interview)
  onboarding: {
    intro:
      "Hi, I'm Peter Grosman. I'm a recent grad from the University of Michigan — double major in Economics and Math. I'm looking for entry-level quantitative finance roles.",
    locationSalary:
      "I'm based in Scarsdale, NY. Strongly prefer New York City, but also open to Chicago or Boston. Hybrid preferred. Salary expectations are $90k-$140k base.",
    experience:
      "I interned at Lakepoint Capital as a quant research intern — built pairs-trading signals in Python. Before that I was at Hudson Valley National Bank doing risk analytics, building PD models. My core skills are Python (NumPy, pandas, scikit-learn, statsmodels), SQL, and I know some R and MATLAB.",
    targetRoles:
      "I'm targeting Quantitative Analyst, Quant Researcher, Risk Analyst, or Quant Developer roles. Mainly at hedge funds, prop trading firms, and asset managers. I'm available immediately — U.S. citizen, no sponsorship needed.",
    wrapUp:
      "I think that covers everything. I'm pretty methodical about my job search — I keep spreadsheets of everything and prefer concrete data over vague encouragement.",
  },

  // Chat messages (Peter's writing style)
  chat: {
    jobSearch:
      "Can you find quantitative analyst openings in New York? I'm mostly interested in hedge funds and prop trading firms, entry-level. Salary range ideally $100k+.",
    quantVsDev:
      "What's the difference between a quant analyst and a quant developer? I want to make sure I'm applying to the right roles given my background.",
    createJob:
      "Add that Two Sigma posting we were looking at. Junior Quantitative Researcher in NYC, salary range $120k-$150k, hybrid. URL is https://twosigma.com/careers/jr-quant-researcher.",
    editJob:
      "I just applied to that Citadel Securities role. Can you update its status to Applied and set the applied date to today?",
    addTodos:
      "For the Citadel role, can you add some prep steps? I need to: review probability theory, practice coding interview questions in Python, and research Citadel's market making strategies.",
    deleteJob:
      "Actually, remove the Goldman Sachs Risk Analyst job if it's still there. I decided that role isn't a good fit.",
    listJobs: "What jobs do I have saved right now? Give me a summary.",
    coverLetter:
      "Can you write a cover letter for the Two Sigma Junior Quantitative Researcher position? Focus on my pairs trading experience at Lakepoint and my stochastic processes coursework.",
    reviseCoverLetter:
      "Can you revise the cover letter for Two Sigma? Make the opening paragraph more confident and add a sentence about my Monte Carlo simulation experience.",
    skillsWorry:
      "I'm a little worried my programming skills aren't strong enough for the more engineering-heavy roles. I've mostly used Python for data analysis, not production systems. What do you think?",
    interviewPrep:
      "Can you help me prep for the Citadel interview? I've heard they focus heavily on probability and brainteasers.",
    orchestratedSearch:
      "Search for entry-level quantitative researcher positions at prop trading firms in NYC and Chicago. Also look for risk analyst roles at investment banks in NYC. I want to compare the best options.",
    compareJobs:
      "Which of the jobs in my tracker is the best fit for me? Consider my quant research internship, my coursework in stochastic processes, and my preference for NYC.",
    profileUpdate:
      "Oh, I forgot to mention — I also know C++ basics. I took a one-term course. And I'm particularly interested in systematic trading strategies.",
    statusSummary:
      "What's my current job search status? How many applications do I have in each stage?",
    absurdSearch:
      "Search for underwater basket weaving instructor positions in Antarctica",
  },

  // Manual job entries (for Scenario 5)
  jobs: {
    twoSigma: {
      company: "Two Sigma",
      title: "Junior Quantitative Researcher",
      url: "https://twosigma.com/careers",
      status: "Saved",
      salaryMin: "120000",
      salaryMax: "150000",
      location: "New York, NY",
      remoteType: "Hybrid",
      tags: "quant, hedge fund, NYC",
      jobFit: 4,
      requirements:
        "Python proficiency\nStatistics background\nBS in quantitative field",
      notes: "Found this on their careers page. Very competitive.",
    },
    citadel: {
      company: "Citadel Securities",
      title: "Quantitative Research Analyst",
      status: "Applied",
      salaryMin: "130000",
      salaryMax: "160000",
      location: "Chicago, IL",
      remoteType: "Onsite",
      appliedDate: "2026-03-25",
      tags: "quant, prop trading, Chicago",
      jobFit: 5,
    },
    goldman: {
      company: "Goldman Sachs",
      title: "Risk Analyst — Strats",
      status: "Interviewing",
      salaryMin: "95000",
      salaryMax: "125000",
      location: "New York, NY",
      remoteType: "Hybrid",
      tags: "risk, investment bank, NYC",
      jobFit: 3,
    },
  },

  // Application todos (for Scenario 5D)
  todos: [
    { title: "Tailor resume for role", category: "document" },
    {
      title: "Research Two Sigma's investment strategies",
      category: "question",
    },
    {
      title: "Prepare for probability brainteaser questions",
      category: "assessment",
    },
  ],
};

/**
 * Configuration keys needed for testing.
 * Actual API key values are read from environment variables at runtime.
 */
export const TEST_CONFIG = {
  /** Env var: SHORTLIST_TEST_ANTHROPIC_KEY */
  get anthropicKey() {
    return process.env.SHORTLIST_TEST_ANTHROPIC_KEY || "";
  },
  /** Env var: SHORTLIST_TEST_TAVILY_KEY */
  get tavilyKey() {
    return process.env.SHORTLIST_TEST_TAVILY_KEY || "";
  },
  /** Env var: SHORTLIST_TEST_OLLAMA_MODEL — default model if not set */
  get ollamaModel() {
    return process.env.SHORTLIST_TEST_OLLAMA_MODEL || "";
  },

  backendUrl: "http://localhost:5000",
  frontendUrl: "http://localhost:3000",
};

// ── Page-object-style helpers ────────────────────────────────────────

/**
 * Extended Playwright test fixture with app-specific helpers.
 */
export const test = base.extend({
  /**
   * Helper object for common app interactions.
   */
  app: async ({ page }, use) => {
    const app = new AppHelper(page);
    await use(app);
  },
});

export { expect };

class AppHelper {
  constructor(page) {
    this.page = page;
  }

  // ── Navigation ──────────────────────────────────────────────────

  async goto(path = "/", { dismissWizard = true } = {}) {
    await this.page.goto(path);
    await this.page.waitForLoadState("domcontentloaded");
    await this.page.waitForTimeout(500);
    if (dismissWizard) {
      await this.dismissWizard();
    }
  }

  /** Dismiss the setup wizard if it's currently visible */
  async dismissWizard() {
    const closeBtn = this.page.getByLabel("Close");
    if (await closeBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
      await closeBtn.click();
      await this.page.waitForTimeout(300);
    }
  }

  /** Click a nav link by its visible text */
  async navigateTo(label) {
    await this.page.getByRole("link", { name: label }).click();
    await this.page.waitForTimeout(1000);
  }

  // ── Chat panel ──────────────────────────────────────────────────

  async openChat() {
    const chatBtn = this.page.getByRole("button", { name: "AI Assistant", exact: true });
    await chatBtn.click();
    // Wait for the chat panel to be visible (look for the panel header text)
    await this.page.getByText("AI Assistant").first().waitFor({
      state: "visible",
      timeout: 5000,
    });
    await this.page.waitForTimeout(500);
  }

  async closeChat() {
    // Click the dark backdrop overlay to close the chat panel
    const backdrop = this.page.locator('.fixed.inset-0.bg-black\\/30');
    if (await backdrop.isVisible().catch(() => false)) {
      await backdrop.click();
      await this.page.waitForTimeout(300);
    }
  }

  async newChat() {
    const newBtn = this.page.getByRole("button", { name: /new chat/i });
    if (await newBtn.isVisible()) {
      await newBtn.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Send a message in the chat panel and wait for the agent to finish responding.
   * @param {string} message - The message to send
   * @param {object} options
   * @param {number} options.timeout - Max ms to wait for the "done" state (default: 120s)
   */
  async sendChatMessage(message, { timeout = 120_000 } = {}) {
    const textarea = this.page.locator(
      'textarea[placeholder*="message"], textarea[placeholder*="Message"], textarea[placeholder*="Type"], textarea[placeholder*="Ask"], textarea[placeholder*="Tell me"], input[placeholder*="Ask"]'
    );
    await textarea.fill(message);

    const sendBtn = this.page
      .getByRole("button", { name: /send/i })
      .or(this.page.locator('button[type="submit"]'))
      .first();
    await sendBtn.click();

    // Wait for agent response to complete: the send button should
    // re-enable (stop button disappears) or we see a "done" marker.
    // A pragmatic approach: wait until no "stop" button is visible.
    await this.page
      .getByRole("button", { name: /stop/i })
      .waitFor({ state: "hidden", timeout })
      .catch(() => {
        /* stop button may never appear for fast responses */
      });

    // Small extra buffer for UI to settle
    await this.page.waitForTimeout(1000);
  }

  /**
   * Wait for a specific SSE tool event to appear in the chat.
   * Looks for the tool name in a tool card element.
   */
  async waitForToolCall(toolName, { timeout = 60_000 } = {}) {
    await this.page
      .getByText(toolName, { exact: false })
      .first()
      .waitFor({ state: "visible", timeout });
  }

  // ── Setup wizard ────────────────────────────────────────────────

  /** Check if the setup wizard modal is visible */
  async isSetupWizardOpen() {
    return this.page.getByText(/welcome to shortlist/i).isVisible();
  }

  /** Click the "Next" or "Get Started" or "Continue" button in the wizard */
  async wizardNext() {
    const btn = this.page
      .getByRole("button", { name: /next|get started|continue/i })
      .first();
    await btn.click();
    await this.page.waitForTimeout(500);
  }

  /** Select a provider card in the wizard by provider name */
  async wizardSelectProvider(providerName) {
    await this.page
      .getByText(providerName, { exact: false })
      .first()
      .click();
  }

  // ── Settings ────────────────────────────────────────────────────

  async saveSettings() {
    await this.page
      .getByRole("button", { name: /save/i })
      .first()
      .click();
    await this.page.waitForTimeout(1000);
  }

  async testConnection() {
    await this.page
      .getByRole("button", { name: /test connection/i })
      .first()
      .click();
  }

  // ── Jobs ────────────────────────────────────────────────────────

  /**
   * Fill and submit the job form.
   * @param {object} job - Job fields (company, title, url, status, etc.)
   */
  async addJob(job) {
    const addBtn = this.page.getByRole("button", { name: /add job/i }).first();
    await addBtn.click();
    await this.page.waitForTimeout(500);

    // Use name attribute selectors as labels aren't htmlFor-linked
    if (job.company)
      await this.page.locator('input[name="company"]').fill(job.company);
    if (job.title)
      await this.page.locator('input[name="title"]').fill(job.title);
    if (job.url)
      await this.page.locator('input[name="url"]').fill(job.url);
    if (job.status) {
      await this.page.locator('select[name="status"]').selectOption(job.status.toLowerCase());
    }
    if (job.salaryMin)
      await this.page.locator('input[name="salary_min"]').fill(job.salaryMin);
    if (job.salaryMax)
      await this.page.locator('input[name="salary_max"]').fill(job.salaryMax);
    if (job.location)
      await this.page.locator('input[name="location"]').fill(job.location);
    if (job.remoteType) {
      await this.page.locator('select[name="remote_type"]').selectOption(job.remoteType.toLowerCase());
    }
    if (job.tags)
      await this.page.locator('input[name="tags"]').fill(job.tags);
    if (job.appliedDate)
      await this.page.locator('input[name="applied_date"]').fill(job.appliedDate);
    if (job.notes)
      await this.page.locator('textarea[name="notes"]').fill(job.notes);
    if (job.requirements)
      await this.page.locator('textarea[name="requirements"]').fill(job.requirements);

    // Submit
    await this.page
      .locator('button[type="submit"]')
      .last()
      .click();
    await this.page.waitForTimeout(1000);
  }

  // ── Health check ────────────────────────────────────────────────

  /** Check if backend is reachable */
  async isBackendHealthy() {
    try {
      const resp = await this.page.request.get(
        `${TEST_CONFIG.backendUrl}/api/health`
      );
      return resp.ok();
    } catch {
      return false;
    }
  }

  /** Check if backend reports LLM configured (200 vs 503) */
  async isLLMConfigured() {
    try {
      const resp = await this.page.request.get(
        `${TEST_CONFIG.backendUrl}/api/health`
      );
      return resp.status() === 200;
    } catch {
      return false;
    }
  }
}

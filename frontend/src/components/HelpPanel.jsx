export default function HelpPanel({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-full max-w-2xl bg-white shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
          <h2 className="font-semibold text-gray-900">Help &amp; Documentation</h2>
          <button onClick={onClose} className="p-1 text-gray-500 hover:text-gray-700">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8">

          {/* Getting Started */}
          <section>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Getting Started</h3>
            <ol className="space-y-3">
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-7 h-7 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-semibold">1</span>
                <div>
                  <p className="font-medium text-gray-800">Configure your AI Assistant</p>
                  <p className="text-sm text-gray-600 mt-0.5">
                    Click the <strong>Settings</strong> (gear icon) button in the top bar. Select your LLM provider, enter your API key, and click <strong>Test Connection</strong> to verify. Then click <strong>Save Settings</strong>.
                  </p>
                </div>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-7 h-7 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-semibold">2</span>
                <div>
                  <p className="font-medium text-gray-800">Complete the onboarding interview</p>
                  <p className="text-sm text-gray-600 mt-0.5">
                    After saving settings for the first time, the AI assistant will automatically start an onboarding interview to learn about your job search goals and preferences.
                  </p>
                </div>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-7 h-7 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-semibold">3</span>
                <div>
                  <p className="font-medium text-gray-800">Start tracking jobs</p>
                  <p className="text-sm text-gray-600 mt-0.5">
                    Add jobs manually using the <strong>+ Add Job</strong> button, or ask the AI assistant to find and add jobs for you — just paste a URL or describe what you're looking for.
                  </p>
                </div>
              </li>
            </ol>
          </section>

          {/* Job Tracking */}
          <section>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Job Tracking</h3>
            <div className="space-y-3 text-sm text-gray-700">
              <div>
                <p className="font-medium text-gray-800 mb-1">Adding and managing jobs</p>
                <ul className="list-disc list-inside space-y-1 text-gray-600">
                  <li>Click <strong>+ Add Job</strong> to manually add a job posting</li>
                  <li>Click any row to open the full job details</li>
                  <li>Use the edit (pencil) icon to update a job's details</li>
                  <li>Use the delete (trash) icon to remove a job</li>
                </ul>
              </div>
              <div>
                <p className="font-medium text-gray-800 mb-1">Job statuses</p>
                <ul className="space-y-1 text-gray-600">
                  <li><span className="inline-block px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-700 font-medium">Saved</span> — Jobs you're interested in but haven't applied to yet</li>
                  <li><span className="inline-block px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-700 font-medium">Applied</span> — You've submitted an application</li>
                  <li><span className="inline-block px-2 py-0.5 rounded text-xs bg-yellow-100 text-yellow-700 font-medium">Interviewing</span> — Active interview process</li>
                  <li><span className="inline-block px-2 py-0.5 rounded text-xs bg-green-100 text-green-700 font-medium">Offer</span> — You've received an offer</li>
                  <li><span className="inline-block px-2 py-0.5 rounded text-xs bg-red-100 text-red-700 font-medium">Rejected</span> — Not moving forward</li>
                </ul>
              </div>
              <div>
                <p className="font-medium text-gray-800 mb-1">Other fields</p>
                <ul className="list-disc list-inside space-y-1 text-gray-600">
                  <li><strong>Job Fit</strong> — Your 1–5 star rating of how well the job matches your goals</li>
                  <li><strong>Remote Type</strong> — Onsite, hybrid, or remote</li>
                  <li><strong>Tags</strong> — Comma-separated labels for filtering and organizing (e.g. "python, fintech, senior")</li>
                  <li><strong>Source</strong> — Where you found the job (e.g. LinkedIn, Indeed, referral)</li>
                </ul>
              </div>
            </div>
          </section>

          {/* AI Chat Assistant */}
          <section>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">AI Chat Assistant</h3>
            <div className="space-y-3 text-sm text-gray-700">
              <p className="text-gray-600">
                Click <strong>AI Assistant</strong> in the top bar to open the chat. The assistant can search the web, look up job postings, scrape URLs, and add jobs directly to your list.
              </p>
              <div>
                <p className="font-medium text-gray-800 mb-1">Example prompts</p>
                <ul className="space-y-1">
                  {[
                    "Find senior Python engineer roles in NYC",
                    "Add this job to my list: [paste URL]",
                    "Summarize this posting and tell me if it's a good fit: [paste URL]",
                    "Search for remote data engineer jobs on LinkedIn",
                    "What jobs have I applied to this month?",
                  ].map((prompt) => (
                    <li key={prompt} className="flex gap-2 text-gray-600">
                      <span className="text-blue-400 flex-shrink-0">›</span>
                      <em>"{prompt}"</em>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="font-medium text-gray-800 mb-1">Available tools</p>
                <ul className="space-y-1.5 text-gray-600">
                  <li><strong>URL scraping</strong> — Always available. Paste any job posting URL and the assistant will read it.</li>
                  <li><strong>Web search</strong> — Requires a <strong>Tavily API key</strong> in Settings. Searches the live web for jobs and company info.</li>
                  <li><strong>Job board search</strong> — Requires a <strong>JSearch</strong> or <strong>Adzuna API key</strong>. Searches real job listings by title, location, and more.</li>
                  <li><strong>Job management</strong> — Always available. The assistant can create, list, and update jobs in your database.</li>
                </ul>
              </div>
            </div>
          </section>

          {/* Getting API Keys */}
          <section>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Getting API Keys</h3>
            <div className="space-y-3">
              <p className="text-sm text-gray-600">You need at least one LLM provider key to use the AI assistant. Integration keys are optional but unlock more features.</p>
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700">LLM Providers (required — pick one)</p>
                <ul className="space-y-1.5 text-sm">
                  {[
                    { name: "Anthropic (Claude)", url: "https://console.anthropic.com/settings/keys" },
                    { name: "OpenAI (GPT)", url: "https://platform.openai.com/api-keys" },
                    { name: "Google Gemini", url: "https://aistudio.google.com/app/apikey" },
                    { name: "Ollama (local, no key needed)", url: "https://ollama.com/" },
                  ].map(({ name, url }) => (
                    <li key={url} className="flex items-center gap-2">
                      <span className="text-blue-400 flex-shrink-0">›</span>
                      <span className="text-gray-700">{name} —</span>
                      <a
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-blue-600 hover:underline break-all"
                      >
                        {url}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700">Integrations</p>
                <ul className="space-y-1.5 text-sm">
                  {[
                    { name: "Tavily — recommended, required for web search", url: "https://app.tavily.com/" },
                    { name: "JSearch via RapidAPI — needed for job board search", url: "https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch" },
                    { name: "Adzuna — job board search, alternative to JSearch", url: "https://developer.adzuna.com/" },
                  ].map(({ name, url }) => (
                    <li key={url} className="flex items-center gap-2">
                      <span className="text-blue-400 flex-shrink-0">›</span>
                      <span className="text-gray-700">{name} —</span>
                      <a
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-blue-600 hover:underline break-all"
                      >
                        {url}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>

          {/* Troubleshooting */}
          <section>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Troubleshooting</h3>
            <div className="space-y-3 text-sm">
              {[
                {
                  problem: "AI chat not working / connection errors",
                  fix: 'Open Settings, verify your provider and API key are correct, and click "Test Connection". Make sure the key hasn\'t expired.',
                },
                {
                  problem: "Job search not finding results",
                  fix: "Job board search requires a JSearch (RapidAPI) or Adzuna API key. Add one in Settings → Integrations.",
                },
                {
                  problem: "Web search not working",
                  fix: "Web search requires a Tavily API key. Get one at app.tavily.com and add it in Settings → Integrations.",
                },
                {
                  problem: '"Rate limit exceeded" errors',
                  fix: "You've hit your API plan's rate limit. Wait a minute and try again, or check your usage on the provider's dashboard.",
                },
                {
                  problem: "App won't start",
                  fix: "Check INSTALLATION.md for setup instructions. If the problem persists, open an issue on GitHub.",
                },
              ].map(({ problem, fix }) => (
                <div key={problem} className="border rounded-lg p-3 bg-gray-50">
                  <p className="font-medium text-gray-800 mb-1">{problem}</p>
                  <p className="text-gray-600">{fix}</p>
                </div>
              ))}
            </div>
          </section>

        </div>
      </div>
    </>
  );
}

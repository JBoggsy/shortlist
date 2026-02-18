import { useState, useEffect } from "react";
import JobList from "./pages/JobList";
import ChatPanel from "./components/ChatPanel";
import ProfilePanel from "./components/ProfilePanel";
import SettingsPanel from "./components/SettingsPanel";
import { fetchOnboardingStatus, fetchHealth } from "./api";

function App() {
  const [chatOpen, setChatOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [onboarding, setOnboarding] = useState(false);
  const [onboardingChecked, setOnboardingChecked] = useState(false);
  const [pendingOnboarding, setPendingOnboarding] = useState(false);
  const [jobsVersion, setJobsVersion] = useState(0);

  function handleJobsChanged() {
    setJobsVersion((v) => v + 1);
  }

  useEffect(() => {
    checkHealthAndOnboarding();
  }, []);

  async function checkHealthAndOnboarding() {
    try {
      // First check if LLM is configured
      const health = await fetchHealth();
      const llmConfigured = health.llm?.configured || false;

      if (!llmConfigured) {
        // LLM not configured - check if user needs onboarding
        const { onboarded } = await fetchOnboardingStatus();
        if (!onboarded) {
          // User needs onboarding but LLM not configured
          // Open Settings and flag to start onboarding after
          setPendingOnboarding(true);
          setSettingsOpen(true);
        }
        // If already onboarded, just let them use the app
        // They can open settings manually if they want to chat
      } else {
        // LLM is configured - check if user needs onboarding
        const { onboarded } = await fetchOnboardingStatus();
        if (!onboarded) {
          setOnboarding(true);
          setChatOpen(true);
        }
      }
    } catch (e) {
      console.error("Failed to check health and onboarding status:", e);
    } finally {
      setOnboardingChecked(true);
    }
  }

  async function handleSettingsSaved() {
    // Called when settings are successfully saved
    // Check if we need to start onboarding now
    if (pendingOnboarding) {
      setPendingOnboarding(false);
      setOnboarding(true);
      setChatOpen(true);
    }
  }

  function handleOnboardingComplete() {
    setOnboarding(false);
    // Keep chat open but switch to normal mode
  }

  function handleChatClose() {
    // Don't allow closing during onboarding
    if (onboarding) return;
    setChatOpen(false);
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Job App Helper</h1>
          <div className="flex gap-2">
            <button
              onClick={() => setSettingsOpen(true)}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center gap-2"
              title="Settings"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Settings
            </button>
            <button
              onClick={() => setProfileOpen(true)}
              className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-800 flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              Profile
            </button>
            <button
              onClick={() => setChatOpen(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              AI Assistant
            </button>
          </div>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-8">
        <JobList refreshVersion={jobsVersion} />
      </main>
      <ChatPanel
        isOpen={chatOpen}
        onClose={handleChatClose}
        onboarding={onboarding}
        onOnboardingComplete={handleOnboardingComplete}
        onJobsChanged={handleJobsChanged}
      />
      <ProfilePanel isOpen={profileOpen} onClose={() => setProfileOpen(false)} />
      <SettingsPanel
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={handleSettingsSaved}
      />
    </div>
  );
}

export default App;

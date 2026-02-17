import { useState, useEffect } from "react";
import JobList from "./pages/JobList";
import ChatPanel from "./components/ChatPanel";
import ProfilePanel from "./components/ProfilePanel";
import { fetchOnboardingStatus } from "./api";

function App() {
  const [chatOpen, setChatOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [onboarding, setOnboarding] = useState(false);
  const [onboardingChecked, setOnboardingChecked] = useState(false);
  const [jobsVersion, setJobsVersion] = useState(0);

  function handleJobsChanged() {
    setJobsVersion((v) => v + 1);
  }

  useEffect(() => {
    checkOnboarding();
  }, []);

  async function checkOnboarding() {
    try {
      const { onboarded } = await fetchOnboardingStatus();
      if (!onboarded) {
        setOnboarding(true);
        setChatOpen(true);
      }
    } catch (e) {
      console.error("Failed to check onboarding status:", e);
    } finally {
      setOnboardingChecked(true);
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
    </div>
  );
}

export default App;

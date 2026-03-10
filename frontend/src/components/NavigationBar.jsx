import { NavLink } from "react-router-dom";
import { useAppContext } from "../contexts/AppContext";

const navLinks = [
  { to: "/", label: "Home", end: true },
  { to: "/jobs", label: "Jobs" },
  { to: "/profile", label: "Profile" },
  { to: "/settings", label: "Settings" },
  { to: "/help", label: "Help" },
];

export default function NavigationBar() {
  const { chatOpen, setChatOpen, onboarding } = useAppContext();

  return (
    <header className="sticky top-0 z-40 bg-white shadow-sm">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <NavLink to="/" className="text-xl font-bold text-gray-900 hover:text-blue-600 transition-colors">
            Shortlist
          </NavLink>
          <nav className="flex gap-1">
            {navLinks.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
        <button
          onClick={() => setChatOpen(!chatOpen)}
          className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
            chatOpen
              ? "bg-blue-700 text-white"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }${onboarding && !chatOpen ? " ring-2 ring-blue-400 ring-offset-2 animate-pulse" : ""}`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          AI Assistant
        </button>
      </div>
    </header>
  );
}

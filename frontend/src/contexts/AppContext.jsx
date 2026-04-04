import { createContext, useContext, useState, useCallback, useRef } from "react";
import { useToast } from "../components/Toast";
import { classifyError, classifyNetworkError } from "../utils/errorClassifier";

const AppContext = createContext();

export function AppProvider({ children }) {
  const [chatOpen, setChatOpen] = useState(false);
  const [onboarding, setOnboarding] = useState(false);
  const [jobsVersion, setJobsVersion] = useState(0);
  const [healthVersion, setHealthVersion] = useState(0);
  const { toasts, addToast, removeToast } = useToast();

  // Document refresh signal — the ChatPanel calls notifyDocumentSaved when
  // it receives a document_saved SSE event, and the DocumentEditorPage
  // subscribes via onDocumentSaved to reload the editor content.
  const documentSavedCallbackRef = useRef(null);

  const notifyDocumentSaved = useCallback((data) => {
    if (documentSavedCallbackRef.current) {
      documentSavedCallbackRef.current(data);
    }
  }, []);

  const onDocumentSaved = useCallback((callback) => {
    documentSavedCallbackRef.current = callback;
    return () => { documentSavedCallbackRef.current = null; };
  }, []);

  const bumpJobsVersion = useCallback(() => {
    setJobsVersion((v) => v + 1);
  }, []);

  const bumpHealthVersion = useCallback(() => {
    setHealthVersion((v) => v + 1);
  }, []);

  const handleChatError = useCallback((rawMessage, source) => {
    const classified = source === "network"
      ? classifyNetworkError(new Error(rawMessage))
      : classifyError(rawMessage);
    addToast(classified);
  }, [addToast]);

  const value = {
    chatOpen,
    setChatOpen,
    onboarding,
    setOnboarding,
    jobsVersion,
    bumpJobsVersion,
    healthVersion,
    bumpHealthVersion,
    notifyDocumentSaved,
    onDocumentSaved,
    toasts,
    addToast,
    removeToast,
    handleChatError,
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useAppContext must be used within AppProvider");
  return ctx;
}

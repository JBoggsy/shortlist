import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { fetchProfile, updateProfile, uploadResume, fetchResume, deleteResume } from "../api";

function ProfilePanel({ isOpen, onClose }) {
  const [content, setContent] = useState("");
  const [editContent, setEditContent] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const textareaRef = useRef(null);

  // Resume state
  const [resumeInfo, setResumeInfo] = useState(null);
  const [resumeUploading, setResumeUploading] = useState(false);
  const [resumeError, setResumeError] = useState(null);
  const [resumeExpanded, setResumeExpanded] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      loadProfile();
      loadResume();
    }
  }, [isOpen]);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isEditing]);

  async function loadProfile() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProfile();
      setContent(data.content);
      setEditContent(data.content);
    } catch (e) {
      setError("Failed to load profile");
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const data = await updateProfile(editContent);
      setContent(data.content);
      setIsEditing(false);
    } catch (e) {
      setError("Failed to save profile");
      console.error(e);
    } finally {
      setSaving(false);
    }
  }

  function handleCancel() {
    setEditContent(content);
    setIsEditing(false);
  }

  async function loadResume() {
    try {
      const data = await fetchResume();
      setResumeInfo(data.resume);
    } catch (e) {
      console.error("Failed to load resume:", e);
    }
  }

  async function handleResumeUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setResumeUploading(true);
    setResumeError(null);
    try {
      const data = await uploadResume(file);
      setResumeInfo({
        filename: data.filename,
        size: data.size,
        text: data.text,
        text_length: data.text_length,
      });
    } catch (err) {
      setResumeError(err.message);
    } finally {
      setResumeUploading(false);
      // Reset the file input so the same file can be re-uploaded
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleResumeDelete() {
    try {
      await deleteResume();
      setResumeInfo(null);
      setResumeExpanded(false);
    } catch (err) {
      setResumeError(err.message);
    }
  }

  function formatFileSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-full max-w-2xl bg-white shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
          <h2 className="font-semibold text-gray-900">User Profile</h2>
          <div className="flex gap-2">
            {!isEditing ? (
              <button
                onClick={() => setIsEditing(true)}
                className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Edit
              </button>
            ) : (
              <>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save"}
                </button>
                <button
                  onClick={handleCancel}
                  disabled={saving}
                  className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:opacity-50"
                >
                  Cancel
                </button>
              </>
            )}
            <button
              onClick={onClose}
              className="p-1 text-gray-500 hover:text-gray-700"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Resume Upload Section */}
          {!isEditing && !loading && (
            <div className="mb-6 border rounded-lg bg-gray-50">
              <div className="px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="font-medium text-gray-900 text-sm">Resume</span>
                  {resumeInfo && (
                    <span className="text-xs text-gray-500">
                      {resumeInfo.filename} ({formatFileSize(resumeInfo.size)})
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {resumeInfo && (
                    <>
                      <button
                        onClick={() => setResumeExpanded(!resumeExpanded)}
                        className="text-xs text-blue-600 hover:text-blue-800"
                      >
                        {resumeExpanded ? "Hide" : "Preview"}
                      </button>
                      <button
                        onClick={handleResumeDelete}
                        className="text-xs text-red-600 hover:text-red-800"
                      >
                        Remove
                      </button>
                    </>
                  )}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx"
                    onChange={handleResumeUpload}
                    className="hidden"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={resumeUploading}
                    className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {resumeUploading ? (
                      <span className="flex items-center gap-1">
                        <span className="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Parsing...
                      </span>
                    ) : resumeInfo ? "Replace" : "Upload"}
                  </button>
                </div>
              </div>
              {resumeError && (
                <div className="px-4 pb-3 text-xs text-red-600">{resumeError}</div>
              )}
              {!resumeInfo && !resumeUploading && (
                <div className="px-4 pb-3 text-xs text-gray-500">
                  Upload your resume (PDF or DOCX) so the AI assistant can reference it when searching for jobs and evaluating fit.
                </div>
              )}
              {resumeExpanded && resumeInfo?.text && (
                <div className="px-4 pb-3 border-t">
                  <pre className="mt-2 text-xs text-gray-700 whitespace-pre-wrap max-h-64 overflow-y-auto bg-white rounded p-3 border">
                    {resumeInfo.text}
                  </pre>
                </div>
              )}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center h-32">
              <span className="inline-block w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : error ? (
            <div className="text-red-600 text-center mt-8">{error}</div>
          ) : isEditing ? (
            <textarea
              ref={textareaRef}
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full h-full min-h-[60vh] p-4 border rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Write your profile in Markdown..."
            />
          ) : (
            <div className="markdown-body prose max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Footer hint */}
        {!isEditing && !loading && (
          <div className="border-t px-4 py-3 text-xs text-gray-500 bg-gray-50">
            This profile is automatically updated by the AI assistant as you chat. You can also edit it manually.
          </div>
        )}
      </div>
    </>
  );
}

export default ProfilePanel;

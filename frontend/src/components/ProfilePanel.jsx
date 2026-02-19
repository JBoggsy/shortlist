import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { fetchProfile, updateProfile, uploadResume, fetchResume, deleteResume, parseResumeWithLLM } from "../api";

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
  const [resumeParsing, setResumeParsing] = useState(false);
  const [resumeError, setResumeError] = useState(null);
  const [resumeExpanded, setResumeExpanded] = useState(false);
  const [resumeView, setResumeView] = useState("structured"); // "structured" or "raw"
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
        parsed: null, // Will be populated after LLM parsing
      });
      // Auto-trigger LLM parsing after upload
      triggerResumeParse();
    } catch (err) {
      setResumeError(err.message);
    } finally {
      setResumeUploading(false);
      // Reset the file input so the same file can be re-uploaded
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function triggerResumeParse() {
    setResumeParsing(true);
    setResumeError(null);
    try {
      const data = await parseResumeWithLLM();
      setResumeInfo(prev => prev ? { ...prev, parsed: data.parsed } : prev);
      setResumeExpanded(true);
    } catch (err) {
      setResumeError(`AI parsing failed: ${err.message}`);
    } finally {
      setResumeParsing(false);
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
                    disabled={resumeUploading || resumeParsing}
                    className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {resumeUploading ? (
                      <span className="flex items-center gap-1">
                        <span className="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Uploading...
                      </span>
                    ) : resumeInfo ? "Replace" : "Upload"}
                  </button>
                </div>
              </div>

              {/* Parsing status */}
              {resumeParsing && (
                <div className="px-4 pb-3 flex items-center gap-2 text-xs text-blue-700">
                  <span className="inline-block w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  AI is analyzing your resume...
                </div>
              )}

              {resumeError && (
                <div className="px-4 pb-3 text-xs text-red-600">{resumeError}</div>
              )}
              {!resumeInfo && !resumeUploading && (
                <div className="px-4 pb-3 text-xs text-gray-500">
                  Upload your resume (PDF or DOCX) so the AI assistant can reference it when searching for jobs and evaluating fit.
                </div>
              )}

              {/* Expanded resume view */}
              {resumeExpanded && resumeInfo && (
                <div className="border-t">
                  {/* View toggle + Re-parse button */}
                  <div className="px-4 py-2 flex items-center justify-between bg-gray-100">
                    <div className="flex gap-1">
                      <button
                        onClick={() => setResumeView("structured")}
                        className={`px-2 py-1 text-xs rounded ${resumeView === "structured" ? "bg-white text-blue-700 shadow-sm font-medium" : "text-gray-600 hover:text-gray-800"}`}
                      >
                        Structured
                      </button>
                      <button
                        onClick={() => setResumeView("raw")}
                        className={`px-2 py-1 text-xs rounded ${resumeView === "raw" ? "bg-white text-blue-700 shadow-sm font-medium" : "text-gray-600 hover:text-gray-800"}`}
                      >
                        Raw Text
                      </button>
                    </div>
                    {resumeInfo.text && (
                      <button
                        onClick={triggerResumeParse}
                        disabled={resumeParsing}
                        className="px-2 py-1 text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50 flex items-center gap-1"
                      >
                        {resumeParsing ? (
                          <>
                            <span className="inline-block w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                            Parsing...
                          </>
                        ) : (
                          <>
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                            Re-parse with AI
                          </>
                        )}
                      </button>
                    )}
                  </div>

                  {resumeView === "structured" ? (
                    resumeInfo.parsed ? (
                      <div className="px-4 py-3">
                        <StructuredResumeView data={resumeInfo.parsed} />
                      </div>
                    ) : (
                      <div className="px-4 py-4 text-center text-xs text-gray-500">
                        {resumeParsing ? (
                          "Parsing in progress..."
                        ) : (
                          <>
                            No structured data yet.{" "}
                            <button onClick={triggerResumeParse} className="text-blue-600 hover:text-blue-800 underline">
                              Parse with AI
                            </button>
                          </>
                        )}
                      </div>
                    )
                  ) : (
                    <div className="px-4 pb-3">
                      <pre className="mt-2 text-xs text-gray-700 whitespace-pre-wrap max-h-64 overflow-y-auto bg-white rounded p-3 border">
                        {resumeInfo.text}
                      </pre>
                    </div>
                  )}
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


// ---------------------------------------------------------------------------
// Structured Resume View
// ---------------------------------------------------------------------------

function StructuredResumeView({ data }) {
  if (!data) return null;

  return (
    <div className="space-y-4 text-sm max-h-96 overflow-y-auto">
      {/* Contact Info */}
      {data.contact_info && (
        <ResumeSection title="Contact">
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {data.contact_info.name && <Field label="Name" value={data.contact_info.name} />}
            {data.contact_info.email && <Field label="Email" value={data.contact_info.email} />}
            {data.contact_info.phone && <Field label="Phone" value={data.contact_info.phone} />}
            {data.contact_info.location && <Field label="Location" value={data.contact_info.location} />}
            {data.contact_info.linkedin && <Field label="LinkedIn" value={data.contact_info.linkedin} link />}
            {data.contact_info.github && <Field label="GitHub" value={data.contact_info.github} link />}
            {data.contact_info.website && <Field label="Website" value={data.contact_info.website} link />}
          </div>
        </ResumeSection>
      )}

      {/* Summary */}
      {data.summary && (
        <ResumeSection title="Summary">
          <p className="text-gray-700">{data.summary}</p>
        </ResumeSection>
      )}

      {/* Work Experience */}
      {data.work_experience?.length > 0 && (
        <ResumeSection title="Experience">
          <div className="space-y-3">
            {data.work_experience.map((exp, i) => (
              <div key={i}>
                <div className="flex justify-between items-start">
                  <div>
                    <span className="font-medium text-gray-900">{exp.title}</span>
                    {exp.company && <span className="text-gray-600"> at {exp.company}</span>}
                  </div>
                  {(exp.start_date || exp.end_date) && (
                    <span className="text-xs text-gray-500 whitespace-nowrap ml-2">
                      {exp.start_date}{exp.end_date ? ` – ${exp.end_date}` : ""}
                    </span>
                  )}
                </div>
                {exp.location && <div className="text-xs text-gray-500">{exp.location}</div>}
                {exp.highlights?.length > 0 && (
                  <ul className="mt-1 space-y-0.5 text-xs text-gray-700">
                    {exp.highlights.map((h, j) => (
                      <li key={j} className="flex gap-1.5">
                        <span className="text-gray-400 mt-0.5 shrink-0">•</span>
                        <span>{h}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </ResumeSection>
      )}

      {/* Education */}
      {data.education?.length > 0 && (
        <ResumeSection title="Education">
          <div className="space-y-2">
            {data.education.map((edu, i) => (
              <div key={i}>
                <div className="flex justify-between items-start">
                  <div>
                    <span className="font-medium text-gray-900">{edu.degree || edu.institution}</span>
                    {edu.degree && edu.institution && <span className="text-gray-600"> – {edu.institution}</span>}
                  </div>
                  {(edu.start_date || edu.end_date) && (
                    <span className="text-xs text-gray-500 whitespace-nowrap ml-2">
                      {edu.start_date}{edu.end_date ? ` – ${edu.end_date}` : ""}
                    </span>
                  )}
                </div>
                {edu.location && <div className="text-xs text-gray-500">{edu.location}</div>}
                {edu.details?.length > 0 && (
                  <ul className="mt-1 text-xs text-gray-600">
                    {edu.details.map((d, j) => <li key={j}>• {d}</li>)}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </ResumeSection>
      )}

      {/* Skills */}
      {data.skills && Object.keys(data.skills).length > 0 && (
        <ResumeSection title="Skills">
          <div className="space-y-1.5">
            {Object.entries(data.skills).map(([category, items]) => (
              items?.length > 0 && (
                <div key={category}>
                  <span className="text-xs font-medium text-gray-600 capitalize">{category}: </span>
                  <span className="text-xs text-gray-700">{Array.isArray(items) ? items.join(", ") : items}</span>
                </div>
              )
            ))}
          </div>
        </ResumeSection>
      )}

      {/* Certifications */}
      {data.certifications?.length > 0 && (
        <ResumeSection title="Certifications">
          <ul className="space-y-1">
            {data.certifications.map((cert, i) => (
              <li key={i} className="text-xs text-gray-700">
                <span className="font-medium">{cert.name}</span>
                {cert.issuer && <span className="text-gray-500"> – {cert.issuer}</span>}
                {cert.date && <span className="text-gray-400"> ({cert.date})</span>}
              </li>
            ))}
          </ul>
        </ResumeSection>
      )}

      {/* Projects */}
      {data.projects?.length > 0 && (
        <ResumeSection title="Projects">
          <div className="space-y-2">
            {data.projects.map((proj, i) => (
              <div key={i}>
                <span className="font-medium text-gray-900 text-xs">{proj.name}</span>
                {proj.description && <p className="text-xs text-gray-600">{proj.description}</p>}
                {proj.technologies?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {proj.technologies.map((t, j) => (
                      <span key={j} className="px-1.5 py-0.5 bg-gray-200 text-gray-700 rounded text-[10px]">{t}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </ResumeSection>
      )}

      {/* Publications */}
      {data.publications?.length > 0 && (
        <ResumeSection title="Publications">
          <ul className="space-y-1">
            {data.publications.map((pub, i) => (
              <li key={i} className="text-xs text-gray-700">
                <span className="font-medium">{pub.title}</span>
                {pub.venue && <span className="text-gray-500"> – {pub.venue}</span>}
                {pub.date && <span className="text-gray-400"> ({pub.date})</span>}
              </li>
            ))}
          </ul>
        </ResumeSection>
      )}

      {/* Awards */}
      {data.awards?.length > 0 && (
        <ResumeSection title="Awards">
          <ul className="space-y-1">
            {data.awards.map((a, i) => (
              <li key={i} className="text-xs text-gray-700">
                <span className="font-medium">{a.name}</span>
                {a.issuer && <span className="text-gray-500"> – {a.issuer}</span>}
                {a.date && <span className="text-gray-400"> ({a.date})</span>}
              </li>
            ))}
          </ul>
        </ResumeSection>
      )}

      {/* Languages */}
      {data.languages?.length > 0 && (
        <ResumeSection title="Languages">
          <div className="flex flex-wrap gap-2">
            {data.languages.map((l, i) => (
              <span key={i} className="text-xs text-gray-700">
                {l.language}{l.proficiency && ` (${l.proficiency})`}
                {i < data.languages.length - 1 ? "," : ""}
              </span>
            ))}
          </div>
        </ResumeSection>
      )}

      {/* Volunteer */}
      {data.volunteer?.length > 0 && (
        <ResumeSection title="Volunteer">
          <div className="space-y-2">
            {data.volunteer.map((v, i) => (
              <div key={i}>
                <div className="flex justify-between items-start">
                  <div>
                    <span className="font-medium text-gray-900 text-xs">{v.role || v.organization}</span>
                    {v.role && v.organization && <span className="text-xs text-gray-600"> at {v.organization}</span>}
                  </div>
                  {(v.start_date || v.end_date) && (
                    <span className="text-[10px] text-gray-500 whitespace-nowrap ml-2">
                      {v.start_date}{v.end_date ? ` – ${v.end_date}` : ""}
                    </span>
                  )}
                </div>
                {v.description && <p className="text-xs text-gray-600">{v.description}</p>}
              </div>
            ))}
          </div>
        </ResumeSection>
      )}
    </div>
  );
}

function ResumeSection({ title, children }) {
  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 border-b pb-1">{title}</h4>
      {children}
    </div>
  );
}

function Field({ label, value, link }) {
  return (
    <div className="text-xs">
      <span className="text-gray-500">{label}: </span>
      {link ? (
        <a
          href={value.startsWith("http") ? value : `https://${value}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:underline"
        >
          {value}
        </a>
      ) : (
        <span className="text-gray-800">{value}</span>
      )}
    </div>
  );
}

export default ProfilePanel;

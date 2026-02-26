import { useState, useEffect, useCallback } from "react";
import { fetchJobTodos, createJobTodo, updateJobTodo, deleteJobTodo, extractJobTodos } from "../api";

const CATEGORY_META = {
  document: { icon: "📄", label: "Documents" },
  question: { icon: "❓", label: "Application Questions" },
  assessment: { icon: "📝", label: "Assessments" },
  reference: { icon: "📋", label: "References" },
  other: { icon: "📌", label: "Other" },
};

const CATEGORY_ORDER = ["document", "question", "assessment", "reference", "other"];

function JobDetailPanel({ job, isOpen, onClose, onEdit }) {
  const [todos, setTodos] = useState([]);
  const [extracting, setExtracting] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTodoTitle, setNewTodoTitle] = useState("");
  const [newTodoCategory, setNewTodoCategory] = useState("other");
  const [newTodoDescription, setNewTodoDescription] = useState("");
  const [expandedTodos, setExpandedTodos] = useState(new Set());
  const [extractError, setExtractError] = useState(null);

  const loadTodos = useCallback(async () => {
    if (!job?.id) return;
    try {
      const data = await fetchJobTodos(job.id);
      setTodos(data);
    } catch (err) {
      console.error("Failed to load todos:", err);
    }
  }, [job?.id]);

  useEffect(() => {
    if (isOpen && job?.id) {
      loadTodos();
      setExtractError(null);
    } else {
      setTodos([]);
    }
  }, [isOpen, job?.id, loadTodos]);

  if (!isOpen || !job) return null;

  const statusColors = {
    saved: "bg-gray-100 text-gray-800",
    applied: "bg-blue-100 text-blue-800",
    interviewing: "bg-yellow-100 text-yellow-800",
    offer: "bg-green-100 text-green-800",
    rejected: "bg-red-100 text-red-800",
  };

  const remoteTypeLabels = {
    onsite: "On-site",
    hybrid: "Hybrid",
    remote: "Remote",
  };

  function formatSalary(min, max) {
    if (!min && !max) return null;
    if (min && max) return `$${min.toLocaleString()} - $${max.toLocaleString()}`;
    if (min) return `$${min.toLocaleString()}+`;
    if (max) return `Up to $${max.toLocaleString()}`;
  }

  async function handleExtract() {
    setExtracting(true);
    setExtractError(null);
    try {
      await extractJobTodos(job.id);
      await loadTodos();
    } catch (err) {
      setExtractError(err.message);
    } finally {
      setExtracting(false);
    }
  }

  async function handleToggleTodo(todo) {
    try {
      const updated = await updateJobTodo(job.id, todo.id, { completed: !todo.completed });
      setTodos((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    } catch (err) {
      console.error("Failed to toggle todo:", err);
    }
  }

  async function handleDeleteTodo(todoId) {
    try {
      await deleteJobTodo(job.id, todoId);
      setTodos((prev) => prev.filter((t) => t.id !== todoId));
    } catch (err) {
      console.error("Failed to delete todo:", err);
    }
  }

  async function handleAddTodo(e) {
    e.preventDefault();
    if (!newTodoTitle.trim()) return;
    try {
      const created = await createJobTodo(job.id, {
        title: newTodoTitle.trim(),
        category: newTodoCategory,
        description: newTodoDescription.trim(),
      });
      setTodos((prev) => [...prev, created]);
      setNewTodoTitle("");
      setNewTodoCategory("other");
      setNewTodoDescription("");
      setShowAddForm(false);
    } catch (err) {
      console.error("Failed to add todo:", err);
    }
  }

  function toggleExpanded(todoId) {
    setExpandedTodos((prev) => {
      const next = new Set(prev);
      if (next.has(todoId)) next.delete(todoId);
      else next.add(todoId);
      return next;
    });
  }

  // Group todos by category
  const grouped = {};
  for (const todo of todos) {
    const cat = todo.category || "other";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(todo);
  }
  const completedCount = todos.filter((t) => t.completed).length;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-full max-w-2xl bg-white shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b bg-gray-50">
          <div className="min-w-0 flex-1">
            <h2 className="font-semibold text-xl text-gray-900">{job.title}</h2>
            <p className="text-gray-600">{job.company}</p>
          </div>
          <div className="flex gap-2 ml-4">
            <button
              onClick={() => onEdit(job)}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Edit
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-500 hover:text-gray-700"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Status Badge */}
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[job.status] || statusColors.saved}`}>
              {job.status || "saved"}
            </span>
            {job.remote_type && (
              <span className="px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
                {remoteTypeLabels[job.remote_type] || job.remote_type}
              </span>
            )}
          </div>

          {/* Job Fit */}
          {job.job_fit != null && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-1">Job Fit</h3>
              <span className="text-amber-500 text-lg">
                {"★".repeat(job.job_fit)}{"☆".repeat(5 - job.job_fit)}
              </span>
              <span className="ml-2 text-sm text-gray-500">{job.job_fit}/5</span>
            </div>
          )}

          {/* Basic Info */}
          {job.location && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-1">Location</h3>
              <p className="text-gray-900">{job.location}</p>
            </div>
          )}

          {formatSalary(job.salary_min, job.salary_max) && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-1">Salary</h3>
              <p className="text-gray-900">{formatSalary(job.salary_min, job.salary_max)}</p>
            </div>
          )}

          {/* URL */}
          {job.url && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-1">Job Posting</h3>
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline break-words"
              >
                {job.url}
              </a>
            </div>
          )}

          {/* Application Steps */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-700">
                Application Steps
                {todos.length > 0 && (
                  <span className="ml-2 text-xs font-normal text-gray-500">
                    {completedCount}/{todos.length} completed
                  </span>
                )}
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowAddForm(!showAddForm)}
                  className="text-xs px-2 py-1 text-gray-600 hover:text-gray-800 border border-gray-300 rounded hover:bg-gray-50"
                  title="Add a custom step"
                >
                  + Add
                </button>
                {job.url && (
                  <button
                    onClick={handleExtract}
                    disabled={extracting}
                    className="text-xs px-2 py-1 text-blue-600 hover:text-blue-800 border border-blue-300 rounded hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Extract application steps from job posting"
                  >
                    {extracting ? (
                      <span className="flex items-center gap-1">
                        <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Extracting…
                      </span>
                    ) : (
                      "Extract from posting"
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* Progress bar */}
            {todos.length > 0 && (
              <div className="w-full bg-gray-200 rounded-full h-1.5 mb-3">
                <div
                  className="bg-green-500 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${(completedCount / todos.length) * 100}%` }}
                />
              </div>
            )}

            {/* Extract error */}
            {extractError && (
              <div className="text-xs text-red-600 bg-red-50 rounded p-2 mb-2">
                {extractError}
              </div>
            )}

            {/* Add form */}
            {showAddForm && (
              <form onSubmit={handleAddTodo} className="bg-gray-50 rounded-lg p-3 mb-3 space-y-2">
                <input
                  type="text"
                  value={newTodoTitle}
                  onChange={(e) => setNewTodoTitle(e.target.value)}
                  placeholder="Step title (e.g., Submit cover letter)"
                  className="w-full px-3 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
                  autoFocus
                />
                <div className="flex gap-2">
                  <select
                    value={newTodoCategory}
                    onChange={(e) => setNewTodoCategory(e.target.value)}
                    className="px-2 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
                  >
                    {CATEGORY_ORDER.map((cat) => (
                      <option key={cat} value={cat}>
                        {CATEGORY_META[cat].icon} {CATEGORY_META[cat].label}
                      </option>
                    ))}
                  </select>
                  <input
                    type="text"
                    value={newTodoDescription}
                    onChange={(e) => setNewTodoDescription(e.target.value)}
                    placeholder="Description (optional)"
                    className="flex-1 px-3 py-1.5 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
                  />
                </div>
                <div className="flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => setShowAddForm(false)}
                    className="text-xs px-3 py-1.5 text-gray-600 hover:text-gray-800"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!newTodoTitle.trim()}
                    className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    Add Step
                  </button>
                </div>
              </form>
            )}

            {/* Grouped todo list */}
            {todos.length > 0 ? (
              <div className="space-y-3">
                {CATEGORY_ORDER.filter((cat) => grouped[cat]?.length > 0).map((cat) => (
                  <div key={cat}>
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <span className="text-sm">{CATEGORY_META[cat].icon}</span>
                      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                        {CATEGORY_META[cat].label}
                      </span>
                    </div>
                    <div className="space-y-1">
                      {grouped[cat].map((todo) => (
                        <div
                          key={todo.id}
                          className={`group flex items-start gap-2 px-3 py-2 rounded-lg border ${
                            todo.completed
                              ? "bg-green-50 border-green-200"
                              : "bg-white border-gray-200 hover:border-gray-300"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={todo.completed}
                            onChange={() => handleToggleTodo(todo)}
                            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-green-600 focus:ring-green-500 cursor-pointer"
                          />
                          <div className="flex-1 min-w-0">
                            <button
                              onClick={() => todo.description && toggleExpanded(todo.id)}
                              className={`text-sm text-left w-full ${
                                todo.completed ? "line-through text-gray-400" : "text-gray-900"
                              } ${todo.description ? "cursor-pointer hover:text-blue-600" : "cursor-default"}`}
                            >
                              {todo.title}
                              {todo.description && (
                                <span className="ml-1 text-gray-400 text-xs">
                                  {expandedTodos.has(todo.id) ? "▾" : "▸"}
                                </span>
                              )}
                            </button>
                            {todo.description && expandedTodos.has(todo.id) && (
                              <p className="text-xs text-gray-500 mt-1 whitespace-pre-wrap">
                                {todo.description}
                              </p>
                            )}
                          </div>
                          <button
                            onClick={() => handleDeleteTodo(todo.id)}
                            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity p-0.5"
                            title="Remove step"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-400 italic">
                {job.url ? "Click \"Extract from posting\" to detect application steps, or add them manually." : "Add application steps manually to track your progress."}
              </p>
            )}
          </div>

          {/* Requirements */}
          {job.requirements && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Requirements</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-gray-900 whitespace-pre-wrap">{job.requirements}</p>
              </div>
            </div>
          )}

          {/* Nice to Haves */}
          {job.nice_to_haves && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Nice to Haves</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-gray-900 whitespace-pre-wrap">{job.nice_to_haves}</p>
              </div>
            </div>
          )}

          {/* Notes */}
          {job.notes && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Notes</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-gray-900 whitespace-pre-wrap">{job.notes}</p>
              </div>
            </div>
          )}

          {/* Tags */}
          {job.tags && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Tags</h3>
              <div className="flex flex-wrap gap-2">
                {job.tags.split(",").map((tag, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm"
                  >
                    {tag.trim()}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Contact Info */}
          {(job.contact_name || job.contact_email) && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Contact</h3>
              <div className="space-y-1">
                {job.contact_name && (
                  <p className="text-gray-900">{job.contact_name}</p>
                )}
                {job.contact_email && (
                  <a
                    href={`mailto:${job.contact_email}`}
                    className="text-blue-600 hover:underline block"
                  >
                    {job.contact_email}
                  </a>
                )}
              </div>
            </div>
          )}

          {/* Application Date */}
          {job.applied_date && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-1">Applied Date</h3>
              <p className="text-gray-900">
                {new Date(job.applied_date).toLocaleDateString()}
              </p>
            </div>
          )}

          {/* Source */}
          {job.source && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-1">Source</h3>
              <p className="text-gray-900">{job.source}</p>
            </div>
          )}

          {/* Timestamps */}
          <div className="pt-4 border-t text-xs text-gray-500">
            <p>Created: {new Date(job.created_at).toLocaleString()}</p>
            <p>Updated: {new Date(job.updated_at).toLocaleString()}</p>
          </div>
        </div>
      </div>
    </>
  );
}

export default JobDetailPanel;

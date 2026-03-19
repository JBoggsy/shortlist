import { marked } from "marked";

// Configure marked for safe, synchronous rendering
marked.setOptions({
  async: false,
  gfm: true,
  breaks: false,
});

/**
 * Detect whether a string is already HTML (from Tiptap editor) or raw markdown
 * (from the AI agent), and convert markdown to HTML if needed.
 */
export function ensureHtml(content) {
  if (!content || !content.trim()) return content;

  // If content already contains block-level HTML tags, treat it as HTML.
  // Tiptap always wraps content in tags like <p>, <h1>, <ul>, etc.
  if (/^<([a-z][a-z0-9]*)\b/i.test(content.trim())) {
    return content;
  }

  // Otherwise it's likely markdown — convert to HTML
  return marked.parse(content);
}

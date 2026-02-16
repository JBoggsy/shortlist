const BASE = "/api/jobs";
const CHAT_BASE = "/api/chat";

export async function fetchJobs() {
  const res = await fetch(BASE);
  if (!res.ok) throw new Error("Failed to fetch jobs");
  return res.json();
}

export async function createJob(data) {
  const res = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create job");
  return res.json();
}

export async function updateJob(id, data) {
  const res = await fetch(`${BASE}/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update job");
  return res.json();
}

export async function deleteJob(id) {
  const res = await fetch(`${BASE}/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete job");
}

// Chat API

export async function fetchConversations() {
  const res = await fetch(`${CHAT_BASE}/conversations`);
  if (!res.ok) throw new Error("Failed to fetch conversations");
  return res.json();
}

export async function createConversation(title) {
  const res = await fetch(`${CHAT_BASE}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("Failed to create conversation");
  return res.json();
}

export async function fetchConversation(id) {
  const res = await fetch(`${CHAT_BASE}/conversations/${id}`);
  if (!res.ok) throw new Error("Failed to fetch conversation");
  return res.json();
}

export async function deleteConversation(id) {
  const res = await fetch(`${CHAT_BASE}/conversations/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete conversation");
}

export async function streamMessage(conversationId, content, onEvent) {
  const res = await fetch(
    `${CHAT_BASE}/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    }
  );

  if (!res.ok) throw new Error("Failed to send message");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = null;
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ") && currentEvent) {
        try {
          const data = JSON.parse(line.slice(6));
          onEvent({ event: currentEvent, data });
        } catch (e) {
          console.error("Failed to parse SSE data:", e);
        }
        currentEvent = null;
      }
    }
  }
}

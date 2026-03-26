---
description: "Generate a project status report summarizing recent completions, in-progress work, and upcoming tasks. Use when the user asks for a status report, project update, catch-up summary, or wants to know where things stand."
---

# Status Report Skill

Generate a concise project status report that enables the user to quickly get up to speed and resume productive work.

## Report Structure

The report MUST answer exactly three questions, presented under these headings:

### 1. Completed Recently
What was finished since the last meaningful milestone or in the recent past.

### 2. Work In Progress
What is actively underway — uncommitted changes, partial implementations, open branches.

### 3. Up Next
What near-term work remains — open TODOs, known bugs, planned features that are next in priority.

## Data Gathering Workflow

Gather all sources **before** writing the report. Use subagents or parallel tool calls where possible for speed.

### Step 1 — Git History
Run these commands to understand recent activity:
```
git --no-pager log --oneline --since="1 week ago" --no-decorate
```
If the log is empty or sparse, widen to `--since="2 weeks ago"`, then `--since="1 month ago"`. Use your judgment on the right window — the goal is to capture the last meaningful batch of work.

For more detail on specific commits when needed:
```
git --no-pager log --since="1 week ago" --stat --no-decorate
```

### Step 2 — Uncommitted Changes
Detect work in progress:
```
git status --short
git --no-pager diff --stat
```
If there are staged or unstaged changes, briefly summarize what files are affected and what the changes appear to do. Read changed files if the diff summary alone is unclear.

### Step 3 — Current Branch Context
```
git branch --show-current
git --no-pager log --oneline -3 HEAD --no-decorate
```
Note if the user is on a feature branch and what it appears to target.

### Step 4 — TODO and Changelog
Read the project's task tracking and changelog files:
- `docs/TODO.md` — scan for checked `[x]` items (recently completed) and unchecked `[ ]` items (remaining work, bugs, planned features)
- `docs/CHANGELOG.md` — scan `[Unreleased]` and the most recent versioned section for context on what shipped and what's staged

### Step 5 — Codebase Inspection (if needed)
Only if the above sources leave ambiguity about what a change does or what's in progress, read relevant source files for clarification. Do NOT do a full codebase scan — be targeted.

## Report Format

Write the report in this exact format:

```markdown
# Status Report — {project name} ({date})

## Completed Recently

**{summary}.** {A short paragraph (2-4 sentences) explaining what was done, why it matters,
and any notable details like files changed, version numbers, or design decisions.}

**{summary}.** {paragraph}

## Work In Progress

**{summary}.** {A short paragraph describing the current state — what's been started,
what remains, and any relevant uncommitted changes or partial implementations.}

(or "No uncommitted changes or in-progress work detected." if clean)

## Up Next

**{summary}.** {A short paragraph explaining what the task involves, why it's next in
priority, and any known context like related bugs, dependencies, or open questions.}
```

## Guidelines

- **Short paragraphs, not bullets.** Each item gets a bold summary sentence followed by a 2-4 sentence paragraph with enough context to understand _what_ and _why_ without reading the code.
- **Group related items.** If five commits all relate to one feature, present them as a single entry, not five.
- **Use specifics.** Reference file names, feature names, and version numbers — not vague summaries.
- **Order by recency/priority.** Most recent completions first, highest-priority upcoming items first.
- **Flag blockers.** If a TODO item or bug looks like it blocks other work, call it out explicitly.
- **Adapt the time window.** If the user specifies a timeframe ("this week", "since v0.12.0"), use that instead of the default 1-week window.
- **Stay factual.** Report what the data shows. Don't speculate about priorities unless TODO.md makes them explicit.

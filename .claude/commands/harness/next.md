---
name: harness-next
description: |
  Get the next task and start working on it.
  Checks for in-progress tasks first, then gets highest priority todo.
---

# Harness Next Task

Get the next task and start working on it.

## Project Context

**Project:** Archon V2 Development
**Project ID:** `b903113d-2a15-4225-888d-c4ff2a8d4389`
**Current Phase:** Phase 1 - Stability

## Instructions

1. **Read context first** (if this is a fresh session):
```
Read docs/LEAD_ENGINEER.md
```
This provides your role, workflow, and key files.

2. **Get next task using MCP tool:**
```
harness_next_task(project_id="b903113d-2a15-4225-888d-c4ff2a8d4389", mark_as_doing=True)
```
This automatically:
- Checks for any "doing" task (resume incomplete work)
- If none, gets highest priority "todo" task
- Marks it as "doing"
- Returns task details

3. **If task found:**
   - Display task title and description
   - Review acceptance criteria
   - Announce: "Starting task: <title>"
   - Create a todo list for implementation steps
   - Begin implementation

4. **If no tasks found:**
   - Check response for "review" tasks count
   - If review tasks exist, inform user
   - If none, announce: "All tasks complete!"

## Usage

User: "/harness-next" or "get next task"

No parameters needed - project_id is hardcoded for Archon V2.

## Workflow
```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Read context     │────►│ harness_next_task│────►│ Start working    │
│ (LEAD_ENGINEER)  │     │ (MCP tool)       │     │ (implement)      │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

## MCP Tool Response

The `harness_next_task` tool returns:
```json
{
  "success": true,
  "task": { "id": "...", "title": "...", "description": "..." },
  "resumed": false,
  "message": "Starting task: ...",
  "remaining_count": 3,
  "prp": {
    "content": "The original specification/requirements...",
    "source_id": "prp_<project_id>",
    "url": "archon://projects/<project_id>/prp"
  },
  "checkpoint": {
    "task_id": "...",
    "step": 3,
    "files_modified": ["src/foo.py", "tests/test_foo.py"],
    "next_action": "Add error handling to parse function",
    "timestamp": "2026-01-14T06:30:00Z"
  },
  "token_estimate": {
    "estimated_tokens": 5500,
    "warning": null,
    "risk_level": "low",
    "breakdown": { "base": 500, "description": 250, "keywords": 2000 }
  }
}
```

- `resumed: true` means continuing an in-progress task
- `resumed: false` means starting a new task
- `remaining_count` shows how many todo tasks remain
- `prp` contains the Project Requirements Plan (if stored via /harness-init)
  - Use the PRP content to understand the original requirements
  - The PRP survives context compaction and is searchable via RAG
- `checkpoint` contains saved progress (only present when resuming)
  - Use this to continue where you left off
  - Shows files already modified and next action to take
  - Save new checkpoints with `/harness-checkpoint` or the MCP tool
- `token_estimate` provides estimated context usage:
  - `estimated_tokens` - Predicted token consumption
  - `risk_level` - "low", "medium", "high", or "critical"
  - `warning` - Present if task may cause context compaction
  - If `risk_level` is high/critical, consider using checkpoints or splitting the task

## Key Files Reference

- **Your context:** `docs/LEAD_ENGINEER.md`
- **Architecture:** `docs/ARCHITECTURE_REFERENCE.md`
- **Roadmap:** `docs/ROADMAP.md`
- **Harness code:** `python/src/mcp_server/features/harness/harness_tools.py`

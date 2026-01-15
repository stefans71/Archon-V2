---
name: harness-checkpoint
description: |
  Save or retrieve task progress for context persistence.
  Helps resume work after session restarts or context compaction.
---

# Harness Checkpoint

Save or retrieve task progress for context persistence across sessions.

## Project Context

**Project:** Archon V2 Development
**Project ID:** `b903113d-2a15-4225-888d-c4ff2a8d4389`

## Purpose

Checkpoints allow work to resume after context compaction by storing:
- Current step in implementation
- Files modified so far
- Next action to take
- Optional notes

## Usage

### Save Progress
```
/harness-checkpoint
```
When prompted, provide:
- **task_id**: Current task UUID (from /harness-next)
- **step**: Current step number (e.g., 3)
- **files_modified**: List of files you've changed
- **next_action**: What needs to happen next

### Get Current Checkpoint
Call the MCP tool with just the task_id to retrieve:
```
harness_checkpoint(task_id="<task-id>")
```

### Clear Checkpoint
When task is complete, clear it:
```
harness_checkpoint(task_id="<task-id>", clear=True)
```

## Example

After modifying several files mid-task:
```
harness_checkpoint(
    task_id="15bc3615-509f-418e-bd24-d02e593833e5",
    step=3,
    files_modified=[
        "python/src/mcp_server/features/harness/harness_tools.py",
        ".claude/commands/harness/checkpoint.md"
    ],
    next_action="Update harness_next_task to include checkpoint in response",
    notes="Created checkpoint tool and slash command"
)
```

## MCP Tool

**Tool**: `harness_checkpoint`

**Arguments**:
- `task_id` (required): UUID of the task
- `step` (optional): Current step number (1-indexed)
- `files_modified` (optional): List of file paths modified
- `next_action` (optional): Description of next action
- `notes` (optional): Additional notes
- `clear` (optional): Set true to clear checkpoint

**Response**:
```json
{
  "success": true,
  "checkpoint": {
    "task_id": "...",
    "step": 3,
    "files_modified": ["src/foo.py"],
    "next_action": "Add error handling",
    "timestamp": "2026-01-15T02:30:00Z"
  },
  "message": "Checkpoint saved for task ...",
  "file_path": "/path/to/.harness/checkpoint.json"
}
```

## File Storage

Checkpoints are stored in `.harness/checkpoint.json` at the repository root.
This file is automatically added to `.gitignore`.

## Integration with /harness-next

When you run `/harness-next` and resume an in-progress task, any existing checkpoint data will be displayed automatically to help you continue where you left off.

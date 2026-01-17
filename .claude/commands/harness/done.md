---
name: harness-done
description: |
  Mark the current task as complete and automatically continue to the next task.
  Creates a git commit and updates CHANGELOG.md.
---

# Harness Done (Autonomous Mode)

Mark the current task as complete and automatically get the next task.

## Autonomous Workflow

This command enables continuous task execution:
1. Complete current task (mark as done)
2. Automatically commit changes to git
3. Update CHANGELOG.md
4. **Automatically get and start the next task**

## What Happens

When you complete a task with `harness_complete`, it automatically:
1. **Runs tests** (unless `skip_tests=true`) - if tests fail, task stays in "doing"
2. Marks the task status as "done" (only if tests pass)
3. Clears any saved checkpoint for the task
4. Creates a git commit (auto_commit is always enabled)
5. Appends a timestamped entry to CHANGELOG.md under `[Unreleased]`
6. **Gets the next task and marks it as "doing"** (auto_continue is enabled by default)

## Instructions

1. Find the current "doing" task:
```
find_tasks(filter_by="status", filter_value="doing")
```

2. If no "doing" task found, inform user and stop.

3. Summarize what was accomplished for this task.

4. Complete the task with auto-commit AND auto-continue:
```
harness_complete(task_id="<task_id>", auto_commit=true)
```

5. Parse the response - it now includes:
   - `task`: The completed task
   - `next_task`: The next task to work on (already marked as "doing")
   - `remaining_count`: Number of remaining todo tasks
   - `all_complete`: True if all tasks are done

6. **If `next_task` exists in the response:**
   - Display the next task title and description
   - Show remaining task count
   - Immediately start working on the next task (no user prompt needed)

7. **If `all_complete` is true:**
   - Congratulate the user - all tasks are done!
   - Suggest running `/harness-status` to review completed work

## Response Format

```json
{
  "success": true,
  "task": { "id": "...", "title": "Completed task", "status": "done" },
  "tests": { "passed": true, "framework": "pytest", "skipped": false },
  "commit": { "hash": "abc123", "message": "feat: ..." },
  "changelog": { "success": true, "entry": "...", "section": "Added" },
  "next_task": {
    "id": "next-task-id",
    "title": "Next task title",
    "description": "What to do next...",
    "status": "doing"
  },
  "remaining_count": 3,
  "all_complete": false
}
```

## Test Verification

By default, `harness_complete` runs tests before marking the task as done.

**If tests PASS:**
- Task is marked as "done"
- Workflow continues normally

**If tests FAIL:**
- Task stays in "doing" status
- Response includes test output in `tests.output`
- Claude must fix the issues and call `harness_complete` again

**To skip tests** (when tests don't exist or aren't applicable):
```
harness_complete(task_id="<id>", auto_commit=true, skip_tests=true)
```

**Supported test frameworks:**
- Python: pytest (detected via pytest.ini, pyproject.toml, or tests/ directory)
- Node.js: npm test (detected via package.json with "test" script)

**Test failure response:**
```json
{
  "success": false,
  "tests": {
    "passed": false,
    "framework": "pytest",
    "output": "... test output showing failures ...",
    "exit_code": 1
  },
  "error": "Tests failed. Fix the issues and try again.",
  "message": "Task not completed - tests failed. The task remains in 'doing' status."
}
```

## Autonomous Loop Behavior

When Claude receives a response with `next_task`:
1. **DO NOT ask the user if they want to continue**
2. **Immediately display the next task and start working on it**
3. This creates a seamless flow from task to task

The loop only stops when:
- `all_complete` is true (no more tasks)
- `next_task` is null
- An error occurs
- User explicitly interrupts

## Commit Message Format

Auto-generated format:
```
feat: <task_title>

Task-ID: <task_id>
```

For custom messages, pass `commit_message`:
```
harness_complete(task_id="<id>", auto_commit=true, commit_message="custom message")
```

## Usage

User: "/harness-done" or "mark task complete"

## Why Auto-Commit?

Git commands run **inside the MCP container** where files are local.
This avoids slow SSHFS operations when Claude Code runs on a remote VPS.

## Changelog Entry Format

Entries are appended to `CHANGELOG.md` under `## [Unreleased]`:

```markdown
### Added
- **2026-01-15 06:30** - Implement checkpoint system (Task: 1852208f)
```

**Section mapping:**
- `feat(...)` titles → `### Added`
- `fix(...)` titles → `### Fixed`
- `refactor(...)` or `chore(...)` → `### Changed`
- Other titles → `### Added` (default)

## Manual Override

If you need to skip auto-commit or auto-continue:
```
harness_complete(task_id="<id>", auto_commit=false, auto_continue=false)
```

To move to review status instead of done:
```
manage_task(action="update", task_id="<task_id>", status="review")
```

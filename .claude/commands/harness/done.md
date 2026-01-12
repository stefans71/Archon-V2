# Harness Done

Mark the current task as complete and commit changes.

## Instructions

1. Verify the current task's acceptance criteria are met
2. Run any relevant tests
3. Stage and commit changes with descriptive message:
```bash
   git add -A
   git commit -m "feat: <task_title> - <brief description of changes>"
```
4. Update task status to "done":
```
   manage_task(action="update", task_id="<id>", status="done")
```
5. Summarize what was accomplished
6. Optionally auto-continue to next task (ask user preference)

## Commit Message Format
```
feat: <task_title>

- Change 1
- Change 2
- Files modified: file1.py, file2.ts

Task-ID: <task_id>
```

## Usage

User: "/harness-done" or "mark task complete"

## Post-Completion Options

- Continue to next task? (y/n)
- Push to remote? (y/n)
- Need review first? (moves to "review" instead of "done")

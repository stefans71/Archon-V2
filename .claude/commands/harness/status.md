# Harness Status

Show project progress overview.

## Instructions

1. Get all tasks for the project:
```
   find_tasks(project_id="<project_id>")
```

2. Display summary table:
```
   Project: <name>
   ─────────────────────────────
   ✅ Done:    X tasks
   🔄 Doing:   X tasks  
   �� Todo:    X tasks
   👀 Review:  X tasks
   ─────────────────────────────
   Progress:   [████████░░] 80%
```

3. List current "doing" task (if any)
4. List next 3 "todo" tasks
5. Show recent git commits (last 3)

## Usage

User: "/harness-status" or "show project status"

## Example Output
```
📊 Archon V2 - Harness Implementation
═══════════════════════════════════════
✅ Done:    4 tasks
🔄 Doing:   1 task (Create /harness-init command)
📋 Todo:    3 tasks
👀 Review:  0 tasks
───────────────────────────────────────
Progress:   [██████░░░░] 50%

🔄 Currently Working On:
   → Create /harness-init command

📋 Up Next:
   1. Create /harness-next command
   2. Create /harness-done command
   3. Test with sample project

📝 Recent Commits:
   - feat: Add CLAUDE_HARNESS.md (2 hours ago)
   - feat: Add Ollama container (1 day ago)
```

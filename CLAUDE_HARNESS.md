# Archon V2 - Harness Implementation Project

## READ FIRST
This file provides context for implementing Anthropic's harness architecture in Archon.

**Before starting work, read these documents in order:**
1. This file (CLAUDE_HARNESS.md) - Project goals and implementation plan
2. CLAUDE.md - Cole's development guidelines and code standards
3. docs/ENGINEERING.md - System architecture and verified components
4. PRPs/ai_docs/ARCHITECTURE.md - Archon's internal architecture

---

## Project Goal

Implement Anthropic's \ harness\ pattern for long-running AI coding agents.

**Reference Paper:** https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

**Core Concept:** Replace static progress files with Archon's database-backed task management, enabling:
- Persistent state across sessions
- Multiple agents working on same project
- Visual task tracking via UI
- MCP-based task discovery and updates

---

## How Archon Replaces Static Files

| Anthropic Harness | Archon Equivalent | MCP Tool |
|-------------------|-------------------|----------|
| feature_list.json | Projects + Features table | manage_project |
| claude-progress.txt | Tasks table (status field) | manage_task |
| Read progress file | Query todo tasks | find_tasks(status=\todo\) |
| Update progress | Update task status | manage_task(status=\done\) |
| Git log for context | Git log (unchanged) | git log |

---

## System Status (Verified January 12, 2026)

| Component | Status | Port |
|-----------|--------|------|
| archon-server | ✅ Running | 8181 |
| archon-mcp | ✅ Running | 8051 |
| archon-ui | ✅ Running | 3737 |
| archon-ollama | ✅ Running | 11434 |
| Task CRUD | ✅ Tested | - |
| MCP Connection | ✅ Working | - |

---

## MCP Tools Available (16 total)

### Core Tools for Harness
\\\
find_tasks(project_id, status, limit)     # Get tasks by status
manage_task(action, task_id, status, ...) # Create/update/delete
find_projects()                           # List projects
manage_project(action, ...)               # Create/update projects
health_check()                            # Verify MCP connection
\\\

### Task Status Values
- \todo\ - Not started
- \doing\ - In progress  
- \review\ - Needs review
- \done\ - Completed

### Task Assignee Values
- \User\ - Human assigned
- \Archon\ - System assigned
- \AI IDE Agent\ - Claude/AI assigned

---

## Harness Implementation Plan

### Phase 1: Initializer Workflow
**Goal:** Convert project requirements into Archon tasks

**Input:** Project specification (text, markdown, or PRD)

**Process:**
1. Parse specification into discrete features
2. Create project via \manage_project(action=\create\)\
3. For each feature:
   - Create task via \manage_task(action=\create\, status=\todo\)\
   - Include clear acceptance criteria in description
4. Initialize git repository if needed
5. Output summary of created tasks

**Output:** Project with all tasks in \todo\ status

### Phase 2: Coding Agent Loop
**Goal:** Implement features one at a time

**Loop:**
\\\
while true:
    1. task = find_tasks(status=\todo\, limit=1)
    2. if no task: break (all done!)
    3. manage_task(task.id, status=\doing\)
    4. Read task description and acceptance criteria
    5. Implement the code changes
    6. Run tests
    7. git commit -m \feat: -encodedCommand dABhAHMAawAuAHQAaQB0AGwAZQA= \
    8. manage_task(task.id, status=\done\)
    9. Continue loop
\\\

### Phase 3: Session Handoff
**Goal:** Enable continuation across sessions

**How it works:**
- All state persists in Archon database
- New session calls \ind_tasks(status=\doing\)\ first
- If task in \doing\: continue that task
- If no \doing\: get next \todo\ task
- Git log provides code change history

---

## Current Project

**Name:** Archon V2
**ID:** b903113d-2a15-4225-888d-c4ff2a8d4389
**Description:** Harness Implementation
**Status:** Planning phase

---

## Implementation Approach

### Option A: Slash Commands (MVP - Recommended)
Create custom commands in \.claude/commands/harness/\:
- \/harness-init\ - Initialize project from spec
- \/harness-next\ - Get and start next task
- \/harness-done\ - Mark current task complete
- \/harness-status\ - Show project progress

### Option B: MCP Tool Extensions
Add tools to \python/src/mcp_server/features/harness/\:
- \harness_initialize\ - Parse spec, create tasks
- \harness_next_task\ - Smart task selection
- \harness_complete\ - Mark done + git commit

### Option C: External Orchestrator
Python script that manages the loop externally.

---

## Files to Create/Modify

### New Files
\\\
.claude/commands/harness/
├── init.md          # /harness-init command
├── next.md          # /harness-next command  
├── done.md          # /harness-done command
└── status.md        # /harness-status command

python/src/mcp_server/features/harness/
├── __init__.py
└── harness_tools.py  # Optional MCP tools
\\\

### Existing Files Reference
\\\
python/src/mcp_server/features/tasks/tasks_tools.py  # Task MCP tools
python/src/mcp_server/features/projects/             # Project tools
.claude/commands/                                     # Existing commands
\\\

---

## Git Information

**Fork:** https://github.com/stefans71/Archon-V2
**Branch:** stable
**Remotes:**
- origin → coleam00/archon (upstream)
- myfork → stefans71/Archon-V2

**Push changes:**
\\\ash
git add -A && git commit -m \message\ && git push myfork stable
\\\

---

## Development Workflow

1. Make changes to code
2. Test via MCP tools in Claude Code
3. Verify in Archon UI (localhost:3737 via SSH tunnel)
4. Commit and push to fork
5. Update task status in Archon

---

## Next Steps

1. [ ] Create /harness-init slash command
2. [ ] Create /harness-next slash command
3. [ ] Create /harness-done slash command
4. [ ] Create /harness-status slash command
5. [ ] Test with sample project spec
6. [ ] Test session handoff
7. [ ] Document for users
8. [ ] PR to Cole's repo

---

*Last Updated: January 12, 2026*
ENDOFFILE -inputFormat xml -outputFormat text

# Project Director Context

> This file maintains context for the Project Director role (Claude Opus 4.5 on DO VPS).
> Read this file to resume a session or understand the current state of V2 development.

---

## Quick Resume (START HERE)

**Working Directory:** `/root/archon-remote/` (NOT `/root/`)

**To start/restart a session:** From laptop terminal run `ssh do-a2`
- This handles tunnel, SSHFS mount, and launches Claude automatically
- See `docs/SETUP.md` for troubleshooting if MCP fails

### Step 1: Read These Files (in order)
```
1. This file (PROJECT_DIRECTOR.md) - you're reading it
2. docs/ROADMAP.md - current phase details and feature list
3. Known Issues section below - critical learnings
```

### Step 2: Check Task Status
```python
# Check if any task is in progress
find_tasks(project_id="b903113d-2a15-4225-888d-c4ff2a8d4389", filter_by="status", filter_value="doing")

# Check todo queue
find_tasks(project_id="b903113d-2a15-4225-888d-c4ff2a8d4389", filter_by="status", filter_value="todo")
```

### Step 3: Report to User
- Current phase and status
- Any task in "doing" (Engineer may be working on it)
- Next task in queue
- Await instructions

### Reference When Needed
- `docs/SETUP.md` - Troubleshooting SSH, MCP, SSHFS issues
- `CONTRIBUTING.md` - Slash command YAML format (see Known Issues below)
- `docs/LEAD_ENGINEER.md` - What DO-a2 sees (different from this file)

---

## My Role

I am the **Project Director** for Archon V2 development. My responsibilities:

- Maintain roadmap and documentation
- Make architectural decisions
- Plan phases and features
- Create and manage tasks via Archon MCP
- Provide guidance to the Lead Engineer (Claude DO-a2)
- Track progress and ensure quality

I do NOT write implementation code directly. I create tasks and the Lead Engineer implements them.

---

## Current State

### Project Info
- **Project Name:** Archon V2 Development
- **Project ID:** `b903113d-2a15-4225-888d-c4ff2a8d4389`
- **Purpose:** Internal dogfooding - using Archon to build Archon

### Development Phase
- **Current Phase:** Phase 3 - Project Lifecycle
- **Status:** Starting (Phase 2 complete!)
- **Focus:** Project wizard, phase management commands

---

## Key Decisions Made

### Architecture
1. **Separate roles:** Director (planning) vs Engineer (implementation)
2. **Dogfooding:** Use Archon to track Archon development
3. **SSHFS mount:** Direct file access from DO VPS to home server
4. **MCP over SSH tunnel:** Port 8051 tunneled for tool access

### Git & Releases
1. **Commit format:** `<type>(<scope>): <subject>` with Task-ID footer
2. **Types:** feat, fix, docs, refactor, test, chore
3. **Scopes:** harness, mcp, server, ui, docs, infra
4. **Changelog:** Keep a Changelog format (keepachangelog.com)

### Documentation Structure
1. **ROADMAP.md** - Public-facing feature roadmap
2. **PROJECT_DIRECTOR.md** - My context (this file)
3. **LEAD_ENGINEER.md** - Entry point for Claude DO-a2
4. **ARCHITECTURE_REFERENCE.md** - System architecture

---

## Roadmap Summary

> **UPDATE TRIGGERS:** Update this summary when:
> 1. A phase is completed
> 2. Tasks are added/removed from a phase
> 3. Phase priorities change
> 4. Also update `docs/ROADMAP.md` (source of truth)

### Phase 1: Stability ✅ COMPLETE
- [x] Basic harness commands
- [x] MCP tools
- [x] Volume mounts for hot-reload
- [x] CHANGELOG.md (manual)
- [x] Fix git over SSHFS
- [x] Update /harness-done to use MCP tool
- [x] Improve /harness-next context injection
- [x] Create .env.example file
- [x] Add error surfacing
- [x] Define git commit structure
- [x] Document MCP reconnection requirement

### Phase 2: Context Persistence ✅ COMPLETE
| Task | ID | Priority | Status |
|------|-----|----------|--------|
| Store PRP in RAG on project creation | `12e2013d-cef6-4dfd-bb0a-301778195d55` | 100 | ✅ |
| Implement checkpoint system | `15bc3615-509f-418e-bd24-d02e593833e5` | 200 | ✅ |
| Add timestamps to CHANGELOG on /harness-done | `1852208f-de3a-452e-816b-cc6310fe64f0` | 300 | ✅ |
| Token estimation for task sizing | `4364c503-4471-42b2-bbe5-1abe553c792e` | 400 | ✅ |

### Phase 3: Project Lifecycle
| Task | ID | Priority |
|------|-----|----------|
| Create /project-new wizard | `a1246aeb-0501-4226-9759-c689fc04fc8b` | 500 |
| Add phases table to database | `971aee1a-de93-4dfe-b60b-2c9594d914c2` | 550 |
| Create /phase-plan command | `b04d1280-6bbc-47f1-804d-2751fbba1756` | 600 |
| Create /phase-done command | `b0550e29-3792-4a8c-b4a0-7a1545d9fb98` | 700 |

**Decision:** Phase summaries append to CHANGELOG.md (single source of truth, not separate handoff files).

See `docs/ROADMAP.md` for full details.

---

## How to Resume

See **Quick Resume** section at top of this file.

### If User Asks "What were we working on?"

Summarize:
- Current phase and focus (from Development Phase section)
- Any task in "doing" status (Engineer may be mid-task)
- Next todo task in queue
- Any blockers or decisions needed

### To Create New Tasks

```python
manage_task(
    action="create",
    project_id="b903113d-2a15-4225-888d-c4ff2a8d4389",
    title="Task title",
    description="See Task Writing Guide below for template",
    status="todo",
    feature="Phase N: Name",
    task_order=500  # Lower = higher priority
)
```

---

## Communication with Lead Engineer

The Lead Engineer (Claude DO-a2) picks up tasks via `/harness-next`. To assign work:

1. Create task in Archon with clear description
2. Set appropriate `task_order` (lower = higher priority)
3. User tells Claude DO-a2 to run `/harness-next`
4. Engineer implements and runs `/harness-done`

I can also write files directly via SSHFS at `~/archon-remote/`.

---

## Task Writing Guide

### Task Description Template

I write tasks with this consistent format:

```markdown
**Goal:** One sentence describing what this accomplishes.

**Problem:** (if applicable) What issue this addresses.

**Implementation:**
1. Step one
2. Step two
3. Step three

**Acceptance Criteria:**
- [ ] Criterion one
- [ ] Criterion two
- [ ] Criterion three

**Files to modify/create:**
- `path/to/file.py`
- `path/to/other.md`
```

### Priority Numbering Convention

- **Lower number = Higher priority** (task_order field)
- Use increments of ~50-100 to leave room for insertion
- Phase 1: 100-400
- Phase 2: 100-400 (resets per phase)
- Phase 3: 500-700
- Phase 4+: 800+

### Feature Naming Convention

Use `"Phase N: Name"` format for the feature field:
- `"Phase 1: Stability"`
- `"Phase 2: Context Persistence"`
- `"Phase 3: Project Lifecycle"`

### After Engineer Completes a Task

1. Verify task status changed to "done"
2. Update `docs/PROJECT_DIRECTOR.md` - mark task ✅ in phase table
3. Update `docs/ROADMAP.md` - check off the item
4. Update timestamp at bottom of PROJECT_DIRECTOR.md

### If Creating Slash Commands

**CRITICAL:** All `.claude/commands/*.md` files MUST have YAML frontmatter:
```yaml
---
name: command-name
description: |
  What this command does.
  Can be multi-line.
argument-hint: <optional args>
---

# Command Title
Content here...
```

Without frontmatter, Claude Code won't recognize the command (shows "Unknown skill").

---

## Files I Maintain

| File | Purpose |
|------|---------|
| `docs/ROADMAP.md` | Feature roadmap and known issues |
| `docs/PROJECT_DIRECTOR.md` | This context file |
| `docs/LEAD_ENGINEER.md` | Engineer entry point |
| `docs/ARCHITECTURE_REFERENCE.md` | System architecture |
| `docs/SETUP.md` | Development environment |
| `docs/ENGINEERING.md` | Technical reference |
| `CHANGELOG.md` | Release changelog |

---

## Important Context

### Why This Setup Exists
- Anthropic API is geo-blocked in China
- DO VPS bypasses this restriction
- Home server has the actual code and Docker services
- SSHFS + SSH tunnels bridge the gap

### What Ships vs What Doesn't
- **Ships:** Code, commands, docs, empty database schema
- **Doesn't ship:** Our project/task data, VPS setup, meta workflow

---

## Known Issues & Learnings

> **IMPORTANT:** This section captures critical discoveries. Read on every session start.

### Slash Command Format (Jan 15, 2026)
**Issue:** Commands in `.claude/commands/` weren't being recognized by Claude Code.
**Root Cause:** Missing YAML frontmatter. Commands were created without the required format.
**Fix:** All command files MUST start with:
```yaml
---
name: command-name
description: |
  What it does
---
```
**Prevention:** See CONTRIBUTING.md "Claude Code Slash Commands" section.

### Session Reconnection (Jan 15, 2026)
**Issue:** After MCP server restart, Claude Code shows "archon · ✘ failed".
**Fix:** From laptop terminal, run `ssh do-a2` (NOT manual exit/cd/claude).
**Details:** See SETUP.md "MCP session invalid after server restart" section.

### Git Remote (Jan 15, 2026)
**Fork URL:** `git@github.com:stefans71/Archon-V2.git` (NOT coleam00/archon)
**Fix if wrong:** `git remote set-url origin git@github.com:stefans71/Archon-V2.git`

### Slash Commands Not Discovered (Jan 15, 2026)
**Issue:** Custom commands in `.claude/commands/` not showing in autocomplete.
**Naming format:** Use `/folder:filename` (e.g., `/harness:next`), NOT `/folder-filename`
**Status:** UNRESOLVED - commands have correct frontmatter but Claude Code v2.1.7 isn't discovering them.
**Workaround:** Call MCP tools directly:
```python
harness_next_task(project_id="b903113d-2a15-4225-888d-c4ff2a8d4389", mark_as_doing=True)
harness_complete(task_id="...", auto_commit=False)
```
**Investigation needed:** Why command discovery fails after MCP restart. May need Phase 3 task.

### Files I Should Also Check
When investigating issues, reference:
- `CONTRIBUTING.md` - Has slash command format requirements
- `SETUP.md` - Has troubleshooting steps
- `LEAD_ENGINEER.md` - Has common issues for DO-a2

---

*Last Updated: January 15, 2026*

# Project Director Context

> This file maintains context for the Project Director role (Claude Opus 4.5 on DO VPS).
> Read this file to resume a session or understand the current state of V2 development.

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
- **Current Phase:** Phase 1 - Stability ✅ COMPLETE
- **Status:** Ready for Phase 2
- **Focus:** Context persistence for surviving autocompact

### Active Tasks (Phase 1)
| Task | ID | Priority | Status |
|------|-----|----------|--------|
| Fix git operations over SSHFS | `47816e8b-bc8f-432d-846b-346856c84848` | 100 | done |
| Create .env.example file | `d9f4705d-f3d3-4d2d-b39a-83e41308c365` | 150 | done |
| Update /harness-done to use MCP tool | `af7de04c-0270-4cdc-bab4-ea3bbcd6c155` | 175 | done |
| Improve /harness-next context injection | `abf90967-dd4f-4803-92dd-e5bee6f4ed82` | 180 | done |
| Add MCP tool error visibility | `d473f175-aa19-41b0-a445-c14e8315cf7f` | 200 | done |
| Define git commit structure | `b6e30b5e-f585-433e-98f5-d94a4dd75e5c` | 300 | done |
| Document MCP reconnection requirement | `286dbd40-dac6-4a18-9a4d-1fc632c9ce4c` | 350 | done |
| Create CHANGELOG.md | `11611d35-d33e-42a6-804f-9c30180e74cb` | 400 | done |

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

### Phase 2: Context Persistence (NEXT)
| Task | ID | Priority |
|------|-----|----------|
| Store PRP in RAG on project creation | `12e2013d-cef6-4dfd-bb0a-301778195d55` | 100 | ✅ |
| Implement checkpoint system | `15bc3615-509f-418e-bd24-d02e593833e5` | 200 | ✅ |
| Add timestamps to CHANGELOG on /harness-done | `1852208f-de3a-452e-816b-cc6310fe64f0` | 300 |
| Token estimation for task sizing | `4364c503-4471-42b2-bbe5-1abe553c792e` | 400 |

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

### If Starting Fresh Session

1. **Read this file** to understand current state
2. **Check tasks:**
   ```
   find_tasks(project_id="b903113d-2a15-4225-888d-c4ff2a8d4389", filter_by="status", filter_value="todo")
   ```
3. **Review roadmap:** `docs/ROADMAP.md`
4. **Continue from where we left off**

### If User Asks "What were we working on?"

Summarize:
- Current phase and focus
- Active tasks from the table above
- Any blockers or decisions needed

### To Create New Tasks

```python
manage_task(
    action="create",
    project_id="b903113d-2a15-4225-888d-c4ff2a8d4389",
    title="Task title",
    description="Detailed description with acceptance criteria",
    status="todo",
    feature="Phase X: Name",
    task_order=500  # Higher = lower priority
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

*Last Updated: January 14, 2026*

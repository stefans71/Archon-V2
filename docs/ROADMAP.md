# Archon V2 - Improvements & Roadmap

## Session Summary (January 12, 2026)

### What We Built Today

1. **Development Environment**
   - DO server as Claude Code host (bypasses China geo-blocking)
   - SSH tunnel for MCP access to China server
   - SSHFS mount for file editing
   - Quick-start script (`ssh do-a2`)

2. **Harness Slash Commands** (`.claude/commands/harness/`)
   - `/harness-init` - Initialize project from spec
   - `/harness-next` - Get and start next task
   - `/harness-done` - Mark task complete
   - `/harness-status` - Show project progress

3. **Harness MCP Tools** (`python/src/mcp_server/features/harness/`)
   - `harness_initialize` - Parse specs, create tasks
   - `harness_next_task` - Smart task selection
   - `harness_complete` - Mark done + git commit

4. **Infrastructure Improvements**
   - Added Ollama to main docker-compose.yml
   - Added volume mount to archon-mcp for hot-reload
   - Documentation in `docs/ENGINEERING.md` and `docs/SETUP.md`

---

## Known Issues & Fixes Needed

### 1. Git Operations Over SSHFS (HIGH)

**Problem:** Git commands via SSHFS are slow/unreliable, causing timeouts.

**Location:** `.claude/commands/harness/done.md`, `harness_tools.py`

**Current Behavior:**
```python
# In harness_tools.py - runs git locally (via SSHFS)
subprocess.run(["git", "add", "-A"], cwd=repo_path)
```

**Fix:** Run git via SSH to home server instead:
```python
# Proposed fix
subprocess.run(["ssh", "home", f"cd ~/archon && git add -A && git commit -m '{message}'"])
```

**Or:** Add configuration option for remote git execution.

---

### 2. Context Loss During Autocompact (CRITICAL)

**Problem:** Claude autocompacts mid-task, losing context of what was being done. This is the core problem - not task granularity.

**Current State:**
- Spec passed as text → parsed → tasks created → spec is GONE after compaction
- No way to resume with full context after compaction
- Work gets lost or repeated

**Solutions:**

#### A. Store Spec in Archon RAG
```
/harness-init
    │
    ▼
┌─────────────────────────────────────┐
│ 1. Save spec to RAG                 │  ← NEW: rag_add_document(project_id, spec)
│ 2. Parse into tasks                 │
│ 3. Link tasks to doc                │
└─────────────────────────────────────┘
    │
    ▼
After compaction, Claude can:
    rag_search_knowledge_base("project spec for Archon V2")
```

#### B. Checkpoint System
```python
# In harness_tools.py - add checkpoint tool
async def harness_checkpoint(task_id: str, state: dict):
    """Save current progress to survive compaction."""
    # Store in task's metadata/description
    manage_task(
        action="update",
        task_id=task_id,
        data={"checkpoint": state}  # files modified, current step, etc.
    )
```

#### C. Progress File in Repo
```python
# Write progress to file that persists
def save_checkpoint(task_id: str, state: dict):
    with open(".harness/checkpoint.json", "w") as f:
        json.dump({
            "task_id": task_id,
            "step": state["current_step"],
            "files_modified": state["files"],
            "next_action": state["next"],
            "timestamp": datetime.now().isoformat()
        }, f)
```

#### D. Context Reconstruction in /harness-next
```markdown
## Updated /harness-next Flow

1. Check for checkpoint file: `.harness/checkpoint.json`
2. If exists and matches current task:
   - Read saved state
   - Resume from `next_action`
3. Read project doc from RAG (always reload)
4. Read current phase summary
5. Read task details
6. NOW start working (with reconstructed context)
```

#### E. Token Estimation for Task Sizing
```python
def estimate_task_tokens(task: dict) -> int:
    """Estimate tokens a task will consume."""
    base_tokens = 500  # Task description, prompts

    if "create file" in task["title"].lower():
        base_tokens += 2000
    if "implement" in task["title"].lower():
        base_tokens += 3000
    if "test" in task["title"].lower():
        base_tokens += 2500
    if "refactor" in task["title"].lower():
        base_tokens += 4000

    files_to_read = task.get("files_to_read", [])
    base_tokens += len(files_to_read) * 1500

    return base_tokens

MAX_TASK_TOKENS = 15000  # Safe limit before splitting
```

---

### 3. Self-Testing Problem (MEDIUM)

**Problem:** AI writes code then writes tests that match its implementation, not the spec.

**Fix Options:**

**Option A: TDD Mode**
- Create tests FIRST based on acceptance criteria
- Then implement to pass tests
- Add `/harness-tdd` command

**Option B: Spec-Based Test Generation**
- Generate test stubs from acceptance criteria, not implementation

**Option C: Review Step**
- Tests go to "review" status
- Human or second agent reviews against spec

---

### 4. MCP Tool Error Visibility (LOW)

**Problem:** Harness tool errors silently logged, not surfaced to user.

**Fix:** Surface registration errors in health_check:
```python
_registration_errors = []

# In health_check tool:
if _registration_errors:
    return {"status": "degraded", "errors": _registration_errors}
```

---

## Project Lifecycle Vision

### The Complete Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROJECT LIFECYCLE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐                                                       │
│  │ 1. PROJECT SETUP │  (Guided wizard - NEW)                                │
│  │    /project-new  │                                                       │
│  └────────┬─────────┘                                                       │
│           │                                                                 │
│           ▼                                                                 │
│  ┌──────────────────┐                                                       │
│  │ 2. PROJECT DOC   │  Stored in Archon Documents + RAG                     │
│  │    (PRP)         │  - Goals, requirements, constraints                   │
│  └────────┬─────────┘  - Tech stack, architecture decisions                 │
│           │                                                                 │
│           ▼                                                                 │
│  ┌──────────────────┐                                                       │
│  │ 3. PHASE PLANNING│  Claude reads PRP, creates Phase 1                    │
│  │    /phase-plan   │  - Defines scope                                      │
│  └────────┬─────────┘  - Estimates tokens                                   │
│           │            - Creates tasks                                      │
│           ▼                                                                 │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │ 4. EXECUTION LOOP (per phase)                            │              │
│  │    ┌─────────┐    ┌─────────┐    ┌─────────┐            │              │
│  │    │ Get     │───►│ Execute │───►│ Test    │            │              │
│  │    │ Task    │    │ Task    │    │ Task    │            │              │
│  │    └─────────┘    └────┬────┘    └────┬────┘            │              │
│  │         ▲              │              │                  │              │
│  │         │              ▼              ▼                  │              │
│  │         │         ┌─────────┐    ┌─────────┐            │              │
│  │         │         │Checkpoint│   │ Mark    │            │              │
│  │         │         │ (save)  │    │ Done    │            │              │
│  │         │         └─────────┘    └────┬────┘            │              │
│  │         │                             │                  │              │
│  │         └─────────────────────────────┘                  │              │
│  │                   (loop until phase complete)            │              │
│  └──────────────────────────────────────────────────────────┘              │
│           │                                                                 │
│           ▼                                                                 │
│  ┌──────────────────┐                                                       │
│  │ 5. PHASE WRITEUP │  Claude summarizes:                                   │
│  │    /phase-done   │  - What was built                                     │
│  └────────┬─────────┘  - Decisions made                                     │
│           │            - Issues encountered                                 │
│           │            - Saved to CHANGELOG                                 │
│           ▼                                                                 │
│  ┌──────────────────┐                                                       │
│  │ 6. NEXT PHASE    │  Claude reads:                                        │
│  │    /phase-plan   │  - Original PRP                                       │
│  └────────┬─────────┘  - Previous phase writeups                            │
│           │            - Creates next phase tasks                           │
│           │                                                                 │
│           ▼                                                                 │
│      (Repeat 4-6 until project complete)                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current vs Needed Features

| Feature | Archon Has? | We Built? | Needed? |
|---------|-------------|-----------|---------|
| Create Project (basic) | ✅ UI + MCP | - | - |
| Guided Project Setup Wizard | ❌ | ❌ | ✅ |
| Add Feature (after setup) | ⚠️ Partial | ❌ | ✅ |
| Add Tasks | ✅ | ✅ harness-init | - |
| Change Log | ❌ | ❌ | ✅ |
| Phase Management | ❌ | ❌ | ✅ |
| Project Document (PRP) | ⚠️ Docs exist, not linked | ❌ | ✅ |
| Phase Write-up/Summary | ❌ | ❌ | ✅ |
| Checkpoint System | ❌ | ❌ | ✅ |

### New Commands Needed

| Command | Purpose |
|---------|---------|
| `/project-new` | Guided wizard to create project + PRP |
| `/project-add-feature` | Add feature to existing project |
| `/phase-plan` | Read PRP, create next phase tasks |
| `/phase-done` | Write summary, update changelog |
| `/harness-checkpoint` | Manual checkpoint save |

### Data Model Changes

```sql
-- Phases table (NEW)
phases (
    id, project_id,
    phase_number, title, description,
    status (planning|active|complete),
    summary,  -- Written at phase end
    created_at, completed_at
)

-- Tasks update
tasks (
    ...existing fields...
    phase_id,           -- Link to phase
    estimated_tokens,   -- For planning
    checkpoint,         -- JSON blob for resume
)

-- Changelog table (NEW)
changelog (
    id, project_id, phase_id,
    entry_type (phase_complete|feature_added|bug_fixed),
    summary, details,
    created_at
)
```

### Where Data Survives Compaction

| Data | Storage | Survives? |
|------|---------|-----------|
| Project Spec/PRP | Archon Document (RAG) | ✅ Yes |
| Task List | Archon Tasks table | ✅ Yes |
| Task Progress | task.data.checkpoint | ✅ Yes |
| Current Step | .harness/checkpoint.json | ✅ Yes |
| Token Estimates | task.data.estimated_tokens | ✅ Yes |
| Code Changes | Git commits | ✅ Yes |

---

## Meta Note: Current Development Mode

**Current state (us building):**
```
Claude (this chat) ──► Building the harness system
                       Using Archon to track our work
                       Modifying Archon code
```

**Future state (user using):**
```
User ──► Starts project via wizard
         │
         ▼
Claude (in harness) ──► CONTAINED to work on user's project
                        Reads PRP from Archon
                        Creates phases/tasks
                        Executes within system boundaries
                        Cannot modify harness itself
```

---

## Feature Roadmap

### Phase 1: Stability (Current)
- [x] Basic harness commands
- [x] MCP tools
- [x] Volume mounts for hot-reload
- [x] Fix git over SSHFS
- [x] Update /harness-done to use MCP tool
- [x] Improve /harness-next context injection
- [x] Add error surfacing
- [x] Create .env.example file
- [x] Define git commit structure
- [x] Document MCP reconnection requirement

### Phase 2: Context Persistence ✅ COMPLETE
- [x] Store PRP in RAG on project creation
- [x] Implement checkpoint system (file + database)
- [x] Add timestamps to CHANGELOG on /harness-done
- [x] Token estimation for task sizing

### Phase 3: Project Lifecycle (ACTIVE)
- [ ] Create /project-new wizard
- [ ] Add phases table to database schema
- [ ] Create /phase-plan command
- [ ] Create /phase-done command (appends to CHANGELOG)

**Decision:** Phase summaries append to CHANGELOG.md (single source of truth, not separate handoff files).

### Phase 4: Intelligence
- [ ] Smarter task decomposition
- [ ] TDD mode
- [ ] Task dependency tracking
- [ ] Auto-split large tasks

### Phase 5: Automation
- [ ] Auto-continue mode (no user prompts)
- [ ] Scheduled runs
- [ ] Progress notifications
- [ ] Multi-project support

### Phase 6: Collaboration
- [ ] Multiple agents on same project
- [ ] Task assignment to specific agents
- [ ] Review workflow
- [ ] PR generation

---

## File Reference

### Harness Commands
```
.claude/commands/harness/
├── init.md      # /harness-init
├── next.md      # /harness-next
├── done.md      # /harness-done
└── status.md    # /harness-status
```

### Harness MCP Tools
```
python/src/mcp_server/features/harness/
├── __init__.py
└── harness_tools.py
    ├── harness_initialize()
    ├── harness_next_task()
    ├── harness_complete()
    ├── _parse_specification()
    ├── _get_todo_count()
    └── _perform_git_commit()
```

### Tests
```
python/tests/mcp_server/features/
└── test_harness_tools.py (22 tests)
```

### Documentation
```
docs/
├── ENGINEERING.md    # System architecture
├── SETUP.md          # Development setup
└── ROADMAP.md        # This file

CLAUDE_HARNESS.md     # Project context for Claude Code
```

---

## Configuration Improvements

### Add to `.claude/settings.local.json`
```json
{
  "permissions": {
    "allow": [
      "mcp__archon__find_tasks",
      "mcp__archon__manage_task",
      "mcp__archon__find_projects",
      "mcp__archon__manage_project",
      "mcp__archon__harness_initialize",
      "mcp__archon__harness_next_task",
      "mcp__archon__harness_complete",
      "Bash(git *)",
      "Bash(cd /root/archon-remote/*)",
      "Write(**/python/**)",
      "Write(**/.claude/**)"
    ]
  }
}
```

### Add MCP config to repo (`.claude/mcp.json`)
```json
{
  "servers": {
    "archon": {
      "transport": "http",
      "url": "http://localhost:8051/mcp"
    }
  }
}
```

---

## Notes for Contributors

### Testing Harness Locally
```bash
# Start services
cd ~/archon && docker compose up -d

# Check MCP tools loaded
docker exec archon-mcp python -c 'from src.mcp_server.features.harness import register_harness_tools; print("OK")'

# Run tests
cd ~/archon/python && python -m pytest tests/mcp_server/features/test_harness_tools.py -v
```

### Adding New Harness Tools
1. Add function to `harness_tools.py`
2. Register in `register_harness_tools()`
3. Add tests to `test_harness_tools.py`
4. Restart archon-mcp (or use hot-reload with volume mount)

---

*Last Updated: January 13, 2026*

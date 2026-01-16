# Changelog

All notable changes to Archon will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Phase 3: Project Lifecycle (January 16, 2026)
- **Phase Management System**
  - Database migration: `001_add_phases_table.sql` (archon_phases table, phase_id on tasks)
  - Phase MCP tools: `find_phases`, `manage_phase`, `assign_task_phase`, `phase_plan_context`
  - Phase service layer: `phase_service.py` with full CRUD + activate/complete operations
  - API endpoints for phase management (9 endpoints)
- **Phase Commands**
  - `/phase-plan` - Plan next phase from PRP + CHANGELOG context
  - `/phase-done` - Complete phase and update CHANGELOG
- **Project Wizard**
  - `/project-new` - Interactive wizard for project creation with PRP generation

#### Phase 2: Context Persistence (January 14-15, 2026)
- **PRP Storage** - Project Requirements Plans stored in RAG (survives context compaction)
- **Checkpoint System** - Save/restore task progress mid-execution
- **Token Estimation** - Risk assessment for task sizing

#### Phase 1: Stability (January 12-13, 2026)
- **Harness System** - Task automation workflow for AI-driven development
  - `/harness-init` - Initialize project from specification
  - `/harness-next` - Get and start next task
  - `/harness-done` - Mark task complete with git commit
  - `/harness-status` - Show project progress
- **Harness MCP Tools**
  - `harness_initialize` - Parse specs and create tasks automatically
  - `harness_next_task` - Smart task selection with resume support
  - `harness_complete` - Mark done with optional git commit
- **Documentation**
  - `docs/ENGINEERING.md` - System architecture reference
  - `docs/SETUP.md` - Development environment setup
  - `docs/ROADMAP.md` - Feature roadmap and known issues
- **Infrastructure**
  - Ollama integration for local embeddings
  - Volume mounts for hot-reload development
  - Docker Compose configuration for Claude Code

### Changed
- Bound all service ports to 127.0.0.1 for security
- Added supabase_default network to all services

### Fixed
- (pending) Git operations over SSHFS reliability

## [2.0.0] - Unreleased

Major rewrite focused on AI-driven development workflows.

### Goals
- Context persistence across sessions (checkpoint system)
- Project lifecycle management (phases, PRPs)
- Intelligent task decomposition
- Multi-agent collaboration support

---

## [1.x.x] - Original Archon

See original repository for pre-V2 changelog.

---

## Commit Message Format

```
<type>(<scope>): <subject>

<body>

Task-ID: <uuid>
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

**Scopes:** `harness`, `mcp`, `server`, `ui`, `docs`, `infra`

**Example:**
```
feat(harness): add checkpoint system for context persistence

- Add harness_checkpoint MCP tool
- Store progress in task.data.checkpoint
- Read checkpoint in /harness-next

Task-ID: 47816e8b-bc8f-432d-846b-346856c84848
```

---
name: phase-done
description: |
  Complete a phase and append summary to CHANGELOG.
  Verifies all tasks are done, generates summary, and prompts for next phase.
---

# Phase Completion Command

Complete the current phase, generate a summary, and append it to CHANGELOG.md.

## Overview

This command guides you through completing a development phase:
1. Verifies all phase tasks are complete
2. Generates a comprehensive phase summary
3. Appends the summary to CHANGELOG.md
4. Prompts for next phase planning

## Project Context

**Project:** Archon V2 Development
**Project ID:** `b903113d-2a15-4225-888d-c4ff2a8d4389`

## Instructions

### Step 1: Identify the Active Phase

Get the current active phase and its tasks:

```
find_phases(project_id="b903113d-2a15-4225-888d-c4ff2a8d4389", status="active", include_tasks=true)
```

If no active phase exists, inform the user and suggest running `/phase-plan` first.

### Step 2: Verify Task Completion

Check that all tasks in the phase are complete:

```
find_tasks(
    project_id="b903113d-2a15-4225-888d-c4ff2a8d4389",
    filter_by="status",
    filter_value="todo"
)
```

**Validation Rules:**
- All tasks with `phase_id` matching the active phase must be `status: "done"`
- If incomplete tasks exist, list them and ask user how to proceed:
  - Complete remaining tasks first
  - Mark them as done anyway
  - Move them to the next phase

### Step 3: Generate Phase Summary

Analyze the completed work and generate a summary:

1. **Review completed tasks** - What was accomplished
2. **Read recent git commits** - Technical changes made
3. **Identify key decisions** - Architecture or design choices
4. **Note any blockers** - Issues encountered and how they were resolved

**Summary Structure:**
```markdown
### Summary
<2-3 sentences describing what was accomplished in this phase>

### Added
- <New features or capabilities>

### Changed
- <Modifications to existing functionality>

### Fixed
- <Bug fixes or issue resolutions>

### Technical Decisions
- <Key architecture or design decisions made>
```

### Step 4: Present Summary for Approval

Show the generated summary to the user:

```
I've generated the following phase summary:

## [Phase X - <Phase Name>] - <YYYY-MM-DD>

<generated summary>

Would you like me to:
1. Append this to CHANGELOG.md and complete the phase
2. Edit the summary first
3. Cancel and continue working
```

Use AskUserQuestion to get user confirmation.

### Step 5: Append to CHANGELOG.md

Read the current CHANGELOG.md and append the phase summary:

```
Read CHANGELOG.md
```

Insert the phase entry **after the `## [Unreleased]` section** and **before any previous phases**:

```markdown
## [Unreleased]

<existing unreleased content>

## [Phase X - <Phase Name>] - YYYY-MM-DD

### Summary
...

### Added
...
```

Use the Edit tool to insert the phase summary at the correct location.

### Step 6: Complete the Phase

Mark the phase as complete with the summary:

```
manage_phase(
    action="complete",
    project_id="b903113d-2a15-4225-888d-c4ff2a8d4389",
    phase_id="<active_phase_id>",
    summary="<brief summary for phase record>"
)
```

### Step 7: Prompt for Next Steps

After completion, display:

```
Phase Completed Successfully!

Phase: <Phase Name>
Tasks Completed: <count>
CHANGELOG Updated: Yes

The phase summary has been appended to CHANGELOG.md.

Next Steps:
- Run `/phase-plan` to plan the next phase
- Run `/harness-status` to see overall project progress
```

## CHANGELOG Phase Entry Format

Use this exact format for phase entries:

```markdown
## [Phase X - <Phase Name>] - YYYY-MM-DD

### Summary
<Concise description of what was accomplished in this phase.>

### Added
- feat(<scope>): <description>
- feat(<scope>): <description>

### Changed
- refactor(<scope>): <description>

### Fixed
- fix(<scope>): <description>

### Technical Decisions
- <Decision made and brief rationale>
```

**Format Guidelines:**
- Use present tense for entries ("Add feature" not "Added feature")
- Include scope in parentheses when relevant
- Keep entries concise but informative
- Technical Decisions section is optional but encouraged

## MCP Tools Used

- `find_phases` - Get active phase and its details
- `find_tasks` - Verify task completion status
- `manage_phase` - Complete the phase with summary
- `AskUserQuestion` - Get user confirmation

## Example Flow

```
User: /phase-done

Claude: Let me check the active phase...

[Calls find_phases with status="active"]

Claude: The active phase is "Phase 3: Project Lifecycle" with 5 tasks.
Let me verify all tasks are complete...

[Calls find_tasks to check status]

Claude: All 5 tasks are complete. Here's the generated summary:

## [Phase 3 - Project Lifecycle] - 2026-01-16

### Summary
Implemented project lifecycle management including the /project-new wizard
for guided project creation, /phase-plan for intelligent phase planning,
and /phase-done for phase completion with CHANGELOG integration.

### Added
- feat(harness): /project-new wizard for guided project setup
- feat(harness): /phase-plan command for AI-driven phase planning
- feat(harness): /phase-done command for phase completion
- feat(mcp): phase_plan_context tool for context gathering

### Technical Decisions
- Store PRPs in RAG for context persistence across sessions
- Use CHANGELOG.md as the primary history record

Would you like me to append this to CHANGELOG.md and complete the phase?

[User confirms]

Claude: Phase completed!
- CHANGELOG.md updated with phase summary
- Phase marked as complete in Archon

Run `/phase-plan` to plan the next phase.
```

## Handling Edge Cases

### No Active Phase
```
Claude: No active phase found.
- Run `/phase-plan` to create and activate a new phase
- Or run `find_phases(project_id="...")` to see all phases
```

### Incomplete Tasks
```
Claude: Found 2 incomplete tasks in this phase:
1. [doing] "Implement feature X"
2. [todo] "Write tests for feature X"

How would you like to proceed?
1. Complete remaining tasks first (recommended)
2. Mark them as done and complete the phase
3. Move them to the next phase
```

### CHANGELOG.md Not Found
```
Claude: CHANGELOG.md not found. Would you like me to create it?
```

## Key Files Reference

- **Phase tools:** `python/src/mcp_server/features/phases/phase_tools.py`
- **Harness tools:** `python/src/mcp_server/features/harness/harness_tools.py`
- **CHANGELOG:** `CHANGELOG.md`
- **Phase plan command:** `.claude/commands/phase/plan.md`

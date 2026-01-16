---
name: phase-plan
description: |
  Read PRP + history and create the next phase with tasks.
  Analyzes project state, determines next logical phase, creates appropriately sized tasks.
---

# Phase Planning Command

Plan and create the next phase for a project based on the PRP and CHANGELOG history.

## Overview

This command guides you through planning a new development phase:
1. Retrieves project context (PRP, CHANGELOG, existing phases)
2. Analyzes what's been done vs. what remains
3. Determines the next logical phase
4. Creates appropriately-sized tasks (30min-4hr each)

## Project Context

**Project:** Archon V2 Development
**Project ID:** `b903113d-2a15-4225-888d-c4ff2a8d4389`

## Instructions

### Step 1: Gather Context

**Option A: Use the convenience tool (requires MCP server restart after adding)**

```
phase_plan_context(project_id="b903113d-2a15-4225-888d-c4ff2a8d4389")
```

**Option B: Gather context manually using existing tools**

```
# 1. Get existing phases
find_phases(project_id="b903113d-2a15-4225-888d-c4ff2a8d4389")

# 2. Get task summary
find_tasks(project_id="...", filter_by="status", filter_value="todo")
find_tasks(project_id="...", filter_by="status", filter_value="done", include_closed=true)

# 3. Read CHANGELOG.md directly
Read CHANGELOG.md file

# 4. Search for PRP in RAG
rag_search_knowledge_base(query="project requirements", source_id="prp_<project_id>")
```

The convenience tool returns:
- **project**: Project title and description
- **prp**: Project Requirements Plan (the original spec/goals)
- **changelog**: CHANGELOG.md content and recent entries
- **phases**: Existing phases and their status
- **task_summary**: Task counts by status (todo, doing, review, done)
- **recommendation**: AI-generated suggestion for next steps

### Step 2: Analyze the Context

Review the returned context and consider:

1. **PRP Analysis**
   - What were the original goals?
   - What features/capabilities were planned?
   - What constraints were identified?

2. **CHANGELOG Review**
   - What has been completed?
   - What phases have been finished?
   - Are there patterns in the work done?

3. **Current State**
   - Are there incomplete phases?
   - Are there pending tasks?
   - What's the logical next step?

### Step 3: Present Phase Options

Present 2-3 phase options to the user using AskUserQuestion:

```
AskUserQuestion(
  questions=[{
    "question": "Based on the PRP and CHANGELOG, which phase should we work on next?",
    "header": "Next Phase",
    "options": [
      {"label": "<Phase Name 1>", "description": "<Brief description of focus>"},
      {"label": "<Phase Name 2>", "description": "<Alternative focus area>"},
      {"label": "Custom", "description": "Define a custom phase focus"}
    ],
    "multiSelect": false
  }]
)
```

### Step 4: Define Phase Goals

Once a phase is selected, define 3-5 concrete goals:

```markdown
## Phase X: <Phase Name>

### Goals
1. <Specific, measurable goal>
2. <Specific, measurable goal>
3. <Specific, measurable goal>

### Scope
- Files to modify: <estimate>
- Estimated tasks: <3-10 tasks>
- Focus areas: <list>
```

### Step 5: Create the Phase

Use the `manage_phase` MCP tool to create the phase:

```
manage_phase(
    action="create",
    project_id="b903113d-2a15-4225-888d-c4ff2a8d4389",
    title="<Phase Name>",
    description="<Phase description>",
    goals=["Goal 1", "Goal 2", "Goal 3"]
)
```

### Step 6: Create Tasks

For each goal, create 1-3 implementable tasks using `manage_task`:

**Task Sizing Guidelines:**
- Each task should be 30 minutes to 4 hours of work
- Tasks should be independently testable
- Include clear acceptance criteria in description
- Order tasks by dependency (task_order: 100, 200, 300...)

```
manage_task(
    action="create",
    project_id="b903113d-2a15-4225-888d-c4ff2a8d4389",
    title="<Action verb> <specific outcome>",
    description="**Goal:** <what to achieve>\n\n**Acceptance Criteria:**\n- [ ] Criterion 1\n- [ ] Criterion 2\n\n**Files to modify:**\n- path/to/file.py",
    assignee="User",
    task_order=100,
    feature="<Phase Name>"
)
```

### Step 7: Activate the Phase (Optional)

If ready to start work immediately:

```
manage_phase(
    action="activate",
    project_id="b903113d-2a15-4225-888d-c4ff2a8d4389",
    phase_id="<phase_id from step 5>"
)
```

### Step 8: Summary

After creating phase and tasks, display:

```
Phase Created Successfully!

Phase: <Phase Name>
Phase ID: <phase_id>
Tasks Created: <count>

Tasks:
1. [todo] <Task 1 title>
2. [todo] <Task 2 title>
3. [todo] <Task 3 title>

Next: Run `/harness-next` to start working on the first task.
```

## Task Description Template

Use this template for task descriptions:

```markdown
**Goal:** <Concise statement of what to accomplish>

**Context:** <Why this task matters, relationship to phase goals>

**Acceptance Criteria:**
- [ ] <Specific, verifiable criterion>
- [ ] <Specific, verifiable criterion>
- [ ] <Tests pass / linting clean if applicable>

**Files to create/modify:**
- `path/to/file.py` - <what to do>
- `path/to/other.py` - <what to do>

**Notes:**
- <Any important constraints or considerations>
```

## MCP Tools Used

- `phase_plan_context` - Gather planning context (PRP, CHANGELOG, phases, tasks)
- `manage_phase` - Create, activate, complete phases
- `manage_task` - Create tasks for the phase
- `find_phases` - Query existing phases
- `find_tasks` - Query existing tasks

## Example Flow

```
User: /phase-plan

Claude: Let me gather the project context...

[Calls phase_plan_context]

Claude: Based on the PRP and CHANGELOG:

**Completed:**
- Phase 1: Stability (git operations, error visibility)
- Phase 2: Context Persistence (PRP storage, checkpoints)

**PRP Goals Remaining:**
- Project lifecycle management
- Intelligent task decomposition
- Multi-agent collaboration

**Recommendation:** Create Phase 3 focusing on project lifecycle.

Which phase would you like to work on next?
[Options presented]

User: Phase 3: Project Lifecycle

Claude: Creating Phase 3 with these goals:
1. /project-new wizard
2. Phase management commands
3. CHANGELOG integration

[Creates phase and tasks]

Claude: Phase 3 created with 5 tasks. Run /harness-next to start.
```

## Key Files Reference

- **Phase tools:** `python/src/mcp_server/features/phases/phase_tools.py`
- **Harness tools:** `python/src/mcp_server/features/harness/harness_tools.py`
- **Task tools:** `python/src/mcp_server/features/tasks/task_tools.py`
- **ROADMAP:** `docs/ROADMAP.md`
- **CHANGELOG:** `CHANGELOG.md`

---
name: project-new
description: |
  Interactive wizard to create a new project with a Project Requirements Plan (PRP).
  Gathers requirements through questions, generates PRP, creates project in Archon.
---

# Project New Wizard

Create a new project through an interactive guided setup.

## Overview

This wizard helps users create a new Archon project with a complete Project Requirements Plan (PRP). The PRP is stored in RAG for context persistence across sessions.

## Instructions

### Step 1: Gather Requirements

Use the `AskUserQuestion` tool to gather project details. Ask these questions in sequence:

**Question 1: Project Name**
```
AskUserQuestion(
  questions=[{
    "question": "What would you like to name this project?",
    "header": "Name",
    "options": [
      {"label": "Feature Project", "description": "Single feature or component"},
      {"label": "Full Application", "description": "Complete application or system"},
      {"label": "Integration", "description": "API integration or connector"}
    ],
    "multiSelect": false
  }]
)
```
The user will likely provide a custom name via "Other".

**Question 2: Goals**
```
AskUserQuestion(
  questions=[{
    "question": "What are you building? Describe the main goals and purpose.",
    "header": "Goals",
    "options": [
      {"label": "New Feature", "description": "Add capability to existing system"},
      {"label": "New Application", "description": "Build from scratch"},
      {"label": "Refactor", "description": "Improve existing code"},
      {"label": "Bug Fix", "description": "Fix issues in existing code"}
    ],
    "multiSelect": false
  }]
)
```

**Question 3: Tech Stack**
```
AskUserQuestion(
  questions=[{
    "question": "What tech stack or constraints should I know about?",
    "header": "Tech Stack",
    "options": [
      {"label": "Python/FastAPI", "description": "Backend with FastAPI"},
      {"label": "React/TypeScript", "description": "Frontend with React"},
      {"label": "Full Stack", "description": "Both frontend and backend"},
      {"label": "Existing Codebase", "description": "Work within existing patterns"}
    ],
    "multiSelect": true
  }]
)
```

**Question 4: Scope**
```
AskUserQuestion(
  questions=[{
    "question": "What's the scope of this project?",
    "header": "Scope",
    "options": [
      {"label": "Small", "description": "Single file or function (1-2 hours)"},
      {"label": "Medium", "description": "Multiple files, single feature (1-2 days)"},
      {"label": "Large", "description": "Cross-cutting changes (3-5 days)"},
      {"label": "Epic", "description": "Major system changes (1+ weeks)"}
    ],
    "multiSelect": false
  }]
)
```

### Step 2: Generate PRP Document

Based on the answers, generate a PRP document in this format:

```markdown
# Project: <name>

## Goals
- <primary goal from user's description>
- <secondary goals>

## Requirements
- <functional requirements derived from goals>
- <non-functional requirements>

## Tech Stack
- <technologies mentioned>
- <frameworks/libraries>

## Constraints
- <technical constraints>
- <scope constraints>
- <time constraints if mentioned>

## Scope
- **Size:** <Small/Medium/Large/Epic>
- **Type:** <Feature/Application/Refactor/Bug Fix>
- **Files:** <estimated files to modify>

## Success Criteria
- [ ] <measurable criteria 1>
- [ ] <measurable criteria 2>
- [ ] <measurable criteria 3>
```

### Step 3: Create Project

Use the `project_initialize` MCP tool to create the project and store the PRP:

```
project_initialize(
    title="<project name>",
    description="<brief description from goals>",
    prp="<the full PRP markdown document>",
    scope="<small|medium|large|epic>",
    create_initial_tasks=false
)
```

This tool:
1. Creates the project in Archon
2. Stores the PRP in RAG (survives context compaction)
3. Returns the new project ID

### Step 4: Offer Next Steps

After project creation, offer the user options:

```
AskUserQuestion(
  questions=[{
    "question": "Project created! What would you like to do next?",
    "header": "Next Step",
    "options": [
      {"label": "Create Tasks", "description": "Break down PRP into tasks with /harness-init"},
      {"label": "Start Coding", "description": "Begin implementing immediately"},
      {"label": "Review PRP", "description": "Refine the requirements first"},
      {"label": "Done for Now", "description": "Continue later"}
    ],
    "multiSelect": false
  }]
)
```

Based on the answer:
- **Create Tasks**: Run `/harness-init` with the PRP
- **Start Coding**: Get the first task with `/harness-next`
- **Review PRP**: Display the PRP and offer to edit
- **Done for Now**: Confirm and end

## Response Format

After successful creation, display:

```
Project Created Successfully!

Name: <project name>
ID: <project_id>
Scope: <scope>

PRP stored in RAG and ready for task creation.

Next: Run `/harness-init` to create tasks from the PRP.
```

## MCP Tools Used

- `project_initialize` - Creates project and stores PRP
- `manage_project` - Fallback for project creation only
- `harness_initialize` - Creates tasks from specification

## Example Flow

```
User: /project-new

Claude: What would you like to name this project?
User: "User Authentication System"

Claude: What are you building? Describe the main goals.
User: "JWT-based auth with OAuth support for Google and GitHub"

Claude: What tech stack or constraints?
User: "Python/FastAPI backend, React frontend, PostgreSQL"

Claude: What's the scope?
User: "Medium - about 3-4 days of work"

Claude: [Generates PRP, creates project, offers next steps]
```

## Key Files Reference

- **Project initialize tool:** `python/src/mcp_server/features/harness/harness_tools.py`
- **PRP storage:** `python/src/mcp_server/features/harness/prp_storage.py`
- **Project management:** `python/src/mcp_server/features/projects/project_tools.py`

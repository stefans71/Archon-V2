---
name: harness-init
description: |
  Initialize a project from a specification.
  Parses the spec and creates tasks in Archon automatically.
argument-hint: <specification text>
---

# Harness Initialize

Initialize a project from a specification by creating tasks in Archon.

## Instructions

1. Read the project specification provided by the user
2. Use the `harness_initialize` MCP tool to parse and create tasks:
```
harness_initialize(
    project_id="<project_id>",
    specification="<the full specification text>",
    assignee="AI IDE Agent",
    feature="<optional feature label>"
)
```

The tool automatically:
- Parses the specification into discrete tasks
- Creates tasks with proper ordering
- **Stores the PRP in RAG for context persistence**

3. After initialization, summarize what was created

## PRP Storage

The specification is stored in the RAG knowledge base as a Project Requirements Plan (PRP):
- **Survives context compaction** - the original requirements are always retrievable
- **Searchable via RAG** - use `rag_search_knowledge_base()` to find relevant requirements
- **Included in /harness-next** - the PRP context is returned when getting the next task

## Usage

User provides: Project specification (text, markdown, or requirements doc)
User provides: Project ID (or create new project first)

## Example

User: "Initialize harness for project b903113d-... with this spec: Build a REST API with /users and /posts endpoints"

```
harness_initialize(
    project_id="b903113d-2a15-4225-888d-c4ff2a8d4389",
    specification="Build a REST API with /users and /posts endpoints",
    feature="REST API"
)
```

Response:
```json
{
  "success": true,
  "tasks_created": 4,
  "tasks": [
    { "id": "...", "title": "Create /users endpoint" },
    { "id": "...", "title": "Create /posts endpoint" },
    { "id": "...", "title": "Add authentication middleware" },
    { "id": "...", "title": "Write API tests" }
  ],
  "prp_stored": true,
  "prp_source_id": "prp_b903113d-..."
}
```

## Key Files Reference

- **Harness tools:** `python/src/mcp_server/features/harness/harness_tools.py`
- **PRP storage:** `python/src/mcp_server/features/harness/prp_storage.py`

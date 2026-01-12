# Harness Initialize

Initialize a project from a specification by creating tasks in Archon.

## Instructions

1. Read the project specification provided by the user
2. Parse it into discrete, implementable features/tasks
3. For each task, call the MCP tool:
```
   manage_task(action="create", project_id="<project_id>", title="<task_title>", description="<detailed_description>", status="todo", assignee="AI IDE Agent")
```
4. Each task description should include:
   - Clear acceptance criteria
   - Files likely to be modified
   - Dependencies on other tasks (if any)
5. After creating all tasks, summarize what was created

## Usage

User provides: Project specification (text, markdown, or requirements doc)
User provides: Project ID (or create new project first)

## Example

User: "Initialize harness for this spec: Build a REST API with /users and /posts endpoints"

Output:
- Task 1: "Create /users endpoint" - CRUD operations for users
- Task 2: "Create /posts endpoint" - CRUD operations for posts  
- Task 3: "Add authentication middleware"
- Task 4: "Write API tests"

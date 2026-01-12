# Harness Next Task

Get the next todo task and start working on it.

## Instructions

1. First check for any task in "doing" status (incomplete from previous session):
```
   find_tasks(project_id="<project_id>", status="doing")
```
   If found, continue that task.

2. If no "doing" task, get next "todo" task:
```
   find_tasks(project_id="<project_id>", status="todo", limit=1)
```

3. If a task is found:
   - Mark it as "doing": `manage_task(action="update", task_id="<id>", status="doing")`
   - Read the task description and acceptance criteria
   - Announce: "Starting task: <title>"
   - Begin implementation

4. If no tasks found:
   - Check for "review" tasks that need attention
   - If none, announce: "All tasks complete!"

## Usage

User: "/harness-next" or "get next task"
Provide: project_id if not obvious from context

## Workflow
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Check doing │────►│ Get todo    │────►│ Start work  │
│ (resume?)   │ no  │ (new task)  │ yes │ (implement) │
└─────────────┘     └─────────────┘     └─────────────┘
       │ yes                                   │
       └───────────────────────────────────────┘
```

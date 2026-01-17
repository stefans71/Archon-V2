"""
Harness tools for Archon MCP Server.

This module provides tools for task automation workflows:
- project_initialize: Create project with PRP stored in RAG
- harness_initialize: Parse specs and create tasks automatically
- harness_next_task: Get next todo task with smart selection
- harness_complete: Mark task done and optionally commit to git
- harness_checkpoint: Save/load task progress for context persistence

Uses HTTP calls to the server service for task operations.
"""

import json
import logging
from urllib.parse import urljoin

import httpx
from mcp.server.fastmcp import Context, FastMCP

from src.mcp_server.utils.error_handling import MCPErrorFormatter
from src.mcp_server.utils.timeout_config import get_default_timeout
from src.server.config.service_discovery import get_api_url

logger = logging.getLogger(__name__)


def register_harness_tools(mcp: FastMCP):
    """Register all harness tools with the MCP server."""

    @mcp.tool()
    async def project_initialize(
        ctx: Context,
        title: str,
        description: str,
        prp: str,
        scope: str = "medium",
        github_repo: str | None = None,
        create_initial_tasks: bool = False,
        task_assignee: str = "AI IDE Agent",
    ) -> str:
        """
        Create a new project with a Project Requirements Plan (PRP) stored in RAG.

        This is the primary tool for the /project-new wizard. It combines:
        1. Project creation in Archon
        2. PRP storage in RAG (survives context compaction)
        3. Optionally creating initial tasks from the PRP

        Args:
            title: Project title (e.g., "User Authentication System")
            description: Brief project description for the project list
            prp: The full Project Requirements Plan in markdown format.
                 This is stored in RAG and used for context during task work.
            scope: Project scope - "small", "medium", "large", or "epic"
            github_repo: Optional GitHub repository URL
            create_initial_tasks: If True, parses the PRP and creates initial tasks
            task_assignee: Default assignee for created tasks (default: "AI IDE Agent")

        Returns:
            JSON with structure:
            - success: bool - Whether project creation succeeded
            - project: dict - The created project details
              - id: str - Project UUID (use this for harness_next_task)
              - title: str - Project title
              - description: str - Project description
            - prp_stored: bool - Whether PRP was stored in RAG
            - prp_source_id: str|null - RAG source ID for the PRP
            - tasks_created: int - Number of tasks created (if create_initial_tasks=True)
            - error: str|null - Error message if failed

        Example PRP format:
            ```markdown
            # Project: User Auth

            ## Goals
            - Implement JWT authentication
            - Add OAuth support

            ## Requirements
            - Login/logout endpoints
            - Token refresh mechanism

            ## Tech Stack
            - Python/FastAPI
            - PostgreSQL

            ## Scope
            - Size: Medium
            - Type: New Feature
            ```

        Usage:
            project_initialize(
                title="User Auth System",
                description="JWT-based authentication with OAuth",
                prp="# Project: User Auth\\n\\n## Goals\\n...",
                scope="medium",
                create_initial_tasks=True
            )
        """
        try:
            if not title or not title.strip():
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message="title is required",
                    suggestion="Provide a project title",
                )

            if not prp or not prp.strip():
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message="prp is required",
                    suggestion="Provide a Project Requirements Plan document",
                )

            # Validate scope
            valid_scopes = ["small", "medium", "large", "epic"]
            if scope.lower() not in valid_scopes:
                scope = "medium"
            else:
                scope = scope.lower()

            api_url = get_api_url()
            timeout = get_default_timeout()

            async with httpx.AsyncClient(timeout=timeout) as client:
                # Step 1: Create the project
                project_data = {
                    "title": title.strip(),
                    "description": description.strip() if description else "",
                }

                if github_repo:
                    project_data["github_repo"] = github_repo

                # Store scope in project metadata/features
                project_data["features"] = {
                    "scope": scope,
                    "has_prp": True,
                }

                response = await client.post(
                    urljoin(api_url, "/api/projects"),
                    json=project_data,
                )

                if response.status_code != 200:
                    return MCPErrorFormatter.from_http_error(response, "create project")

                result = response.json()
                project = result.get("project", {})
                project_id = project.get("id")

                if not project_id:
                    return MCPErrorFormatter.format_error(
                        error_type="server_error",
                        message="Project created but no ID returned",
                        suggestion="Check server logs for details",
                    )

                logger.info(f"Created project {project_id}: {title}")

            # Step 2: Store PRP in RAG
            prp_result = None
            try:
                from src.mcp_server.features.harness.prp_storage import store_prp_in_rag

                prp_result = await store_prp_in_rag(
                    project_id=project_id,
                    project_title=title,
                    specification=prp,
                )
                if prp_result.get("success"):
                    logger.info(f"PRP stored in RAG for project {project_id}")
                else:
                    logger.warning(f"Failed to store PRP in RAG: {prp_result.get('error')}")
            except Exception as prp_error:
                logger.warning(f"Error storing PRP in RAG (non-fatal): {prp_error}")
                prp_result = {"success": False, "error": str(prp_error)}

            # Step 3: Optionally create initial tasks
            tasks_created = 0
            created_tasks = []
            if create_initial_tasks:
                task_items = _parse_specification(prp)
                if task_items:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        for idx, item in enumerate(task_items):
                            task_data = {
                                "project_id": project_id,
                                "title": item["title"],
                                "description": item.get("description", ""),
                                "assignee": task_assignee,
                                "task_order": (idx + 1) * 100,
                                "sources": [],
                                "code_examples": [],
                            }

                            task_response = await client.post(
                                urljoin(api_url, "/api/tasks"),
                                json=task_data,
                            )

                            if task_response.status_code == 200:
                                task_result = task_response.json()
                                task = task_result.get("task", {})
                                created_tasks.append({
                                    "id": task.get("id"),
                                    "title": task.get("title"),
                                })
                                tasks_created += 1

            return json.dumps({
                "success": True,
                "project": {
                    "id": project_id,
                    "title": project.get("title"),
                    "description": project.get("description"),
                },
                "prp_stored": prp_result.get("success") if prp_result else False,
                "prp_source_id": prp_result.get("source_id") if prp_result else None,
                "tasks_created": tasks_created,
                "tasks": created_tasks if created_tasks else None,
                "message": f"Project '{title}' created successfully",
                "next_steps": [
                    f"Use harness_next_task(project_id='{project_id}') to get tasks",
                    f"Use harness_initialize(project_id='{project_id}', specification='...') to add more tasks",
                ],
            })

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(
                e, "initialize project", {"title": title}
            )
        except Exception as e:
            logger.error(f"Error initializing project: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, "initialize project")

    @mcp.tool()
    async def harness_initialize(
        ctx: Context,
        project_id: str,
        specification: str,
        assignee: str = "AI IDE Agent",
        feature: str | None = None,
    ) -> str:
        """
        Initialize a project by parsing a specification and creating tasks automatically.

        This tool parses a specification document and creates discrete, implementable
        tasks in the specified project.

        Args:
            project_id: UUID of the project to add tasks to
            specification: The specification text to parse into tasks.
                          Can be plain text, markdown, or numbered list.
                          Each line/item will be analyzed for task extraction.
            assignee: Default assignee for created tasks (default: "AI IDE Agent")
            feature: Optional feature label to group all created tasks

        Returns:
            JSON with structure:
            - success: bool - Whether initialization succeeded
            - tasks_created: int - Number of tasks created
            - tasks: list[dict] - Array of created task summaries
            - errors: list|null - Array of task creation errors if any
            - project_id: str - The project ID
            - prp_stored: bool - Whether the PRP was stored in RAG
            - prp_source_id: str|null - RAG source ID for the stored PRP

        Example specification formats:
            "1. Create user model\\n2. Add authentication\\n3. Write tests"
            "- Setup database schema\\n- Implement API endpoints\\n- Add validation"
            "Build login page. Add form validation. Connect to auth API."
        """
        try:
            if not project_id:
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message="project_id is required",
                    suggestion="Provide a valid project UUID",
                )

            if not specification or not specification.strip():
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message="specification is required and cannot be empty",
                    suggestion="Provide a specification with tasks to create",
                )

            # Parse specification into task items
            task_items = _parse_specification(specification)

            if not task_items:
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message="Could not parse any tasks from specification",
                    suggestion="Ensure specification contains clear task descriptions",
                )

            api_url = get_api_url()
            timeout = get_default_timeout()

            created_tasks = []
            errors = []

            async with httpx.AsyncClient(timeout=timeout) as client:
                # First verify project exists and get project details
                project_response = await client.get(
                    urljoin(api_url, f"/api/projects/{project_id}")
                )

                if project_response.status_code == 404:
                    return MCPErrorFormatter.format_error(
                        error_type="not_found",
                        message=f"Project {project_id} not found",
                        suggestion="Verify the project_id is correct",
                        http_status=404,
                    )
                elif project_response.status_code != 200:
                    return MCPErrorFormatter.from_http_error(project_response, "verify project")

                # Get project title for PRP storage
                project_data = project_response.json()
                project_title = project_data.get("title", "Untitled Project")

                # Create tasks with incrementing order
                for idx, item in enumerate(task_items):
                    task_data = {
                        "project_id": project_id,
                        "title": item["title"],
                        "description": item.get("description", ""),
                        "assignee": assignee,
                        "task_order": (idx + 1) * 100,  # 100, 200, 300, etc.
                        "sources": [],
                        "code_examples": [],
                    }

                    if feature:
                        task_data["feature"] = feature

                    response = await client.post(
                        urljoin(api_url, "/api/tasks"),
                        json=task_data,
                    )

                    if response.status_code == 200:
                        result = response.json()
                        task = result.get("task", {})
                        created_tasks.append({
                            "id": task.get("id"),
                            "title": task.get("title"),
                            "task_order": task.get("task_order"),
                        })
                    else:
                        errors.append({
                            "title": item["title"],
                            "error": f"HTTP {response.status_code}",
                        })

            # Store PRP in RAG for context persistence
            prp_result = None
            if len(created_tasks) > 0:
                try:
                    from src.mcp_server.features.harness.prp_storage import store_prp_in_rag

                    prp_result = await store_prp_in_rag(
                        project_id=project_id,
                        project_title=project_title,
                        specification=specification,
                    )
                    if prp_result.get("success"):
                        logger.info(f"PRP stored in RAG for project {project_id}")
                    else:
                        logger.warning(f"Failed to store PRP in RAG: {prp_result.get('error')}")
                except Exception as prp_error:
                    logger.warning(f"Error storing PRP in RAG (non-fatal): {prp_error}")
                    prp_result = {"success": False, "error": str(prp_error)}

            return json.dumps({
                "success": len(created_tasks) > 0,
                "tasks_created": len(created_tasks),
                "tasks": created_tasks,
                "errors": errors if errors else None,
                "project_id": project_id,
                "prp_stored": prp_result.get("success") if prp_result else False,
                "prp_source_id": prp_result.get("source_id") if prp_result else None,
            })

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(
                e, "initialize harness", {"project_id": project_id}
            )
        except Exception as e:
            logger.error(f"Error initializing harness: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, "initialize harness")

    @mcp.tool()
    async def harness_next_task(
        ctx: Context,
        project_id: str,
        mark_as_doing: bool = True,
    ) -> str:
        """
        Get the next task to work on with smart selection.

        Checks for any task already in "doing" status first (resume scenario),
        then gets the highest priority "todo" task based on task_order.

        Args:
            project_id: UUID of the project to get tasks from
            mark_as_doing: If True, automatically marks the task as "doing"
                          (default: True)

        Returns:
            JSON with structure:
            - success: bool - Whether a task was found
            - task: dict|null - The task to work on (full details)
            - resumed: bool - Whether this is resuming an in-progress task
            - message: str - Status message
            - remaining_count: int - Number of remaining todo tasks
            - prp: dict|null - Project Requirements Plan context (if available)
              - content: str - The full PRP/specification text
              - source_id: str - RAG source identifier
              - url: str - Internal URL for the PRP
            - phase: dict|null - Current phase context (if task is in a phase)
              - id: str - Phase UUID
              - phase_number: int - Phase sequence number
              - title: str - Phase title
              - description: str - Phase description
              - status: str - Phase status (planning, active, complete)
              - goals: list - Phase goals
            - checkpoint: dict|null - Saved progress for resumed tasks
              - step: int - Current step number
              - files_modified: list - Files changed so far
              - next_action: str - What to do next
              - timestamp: str - When checkpoint was saved
            - token_estimate: dict - Estimated token usage for the task
              - estimated_tokens: int - Total estimated tokens
              - warning: str|null - Warning if task is large
              - risk_level: str - "low", "medium", "high", or "critical"
              - breakdown: dict - Token breakdown by category

        Workflow:
            1. Check for existing "doing" tasks (resume incomplete work)
            2. If none, get highest priority "todo" task (lowest task_order)
            3. Optionally mark as "doing" before returning
            4. Return task details for implementation
        """
        try:
            if not project_id:
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message="project_id is required",
                    suggestion="Provide a valid project UUID",
                )

            api_url = get_api_url()
            timeout = get_default_timeout()

            async with httpx.AsyncClient(timeout=timeout) as client:
                # First check for any task already in "doing" status
                doing_response = await client.get(
                    urljoin(api_url, "/api/tasks"),
                    params={
                        "project_id": project_id,
                        "status": "doing",
                        "per_page": 1,
                    },
                )

                if doing_response.status_code == 200:
                    doing_result = doing_response.json()
                    doing_tasks = doing_result.get("tasks", [])

                    if doing_tasks:
                        # Resume existing task
                        task = doing_tasks[0]

                        # Get remaining todo count
                        todo_count = await _get_todo_count(client, api_url, project_id)

                        # Get PRP context for the project
                        prp_context = await _get_prp_context(project_id)

                        # Get checkpoint data for resumed task
                        checkpoint = await _get_checkpoint_for_task(task.get("id"))

                        # Get phase context if task is in a phase
                        phase_context = await _get_phase_context(project_id, task.get("phase_id"))

                        # Estimate task tokens
                        token_estimate = _estimate_task_tokens(task)

                        return json.dumps({
                            "success": True,
                            "task": task,
                            "resumed": True,
                            "message": f"Resuming in-progress task: {task.get('title')}",
                            "remaining_count": todo_count,
                            "prp": prp_context,
                            "phase": phase_context,
                            "checkpoint": checkpoint,
                            "token_estimate": token_estimate,
                        })

                # No doing task, get next todo task
                todo_response = await client.get(
                    urljoin(api_url, "/api/tasks"),
                    params={
                        "project_id": project_id,
                        "status": "todo",
                        "per_page": 100,  # Get more to find lowest order
                        "include_closed": False,
                    },
                )

                if todo_response.status_code != 200:
                    return MCPErrorFormatter.from_http_error(todo_response, "get todo tasks")

                todo_result = todo_response.json()
                todo_tasks = todo_result.get("tasks", [])

                if not todo_tasks:
                    # Check for review tasks
                    review_response = await client.get(
                        urljoin(api_url, "/api/tasks"),
                        params={
                            "project_id": project_id,
                            "status": "review",
                            "per_page": 1,
                        },
                    )

                    review_count = 0
                    if review_response.status_code == 200:
                        review_result = review_response.json()
                        review_count = len(review_result.get("tasks", []))

                    return json.dumps({
                        "success": False,
                        "task": None,
                        "resumed": False,
                        "message": "All tasks complete!" if review_count == 0 else f"No todo tasks. {review_count} task(s) in review.",
                        "remaining_count": 0,
                        "review_count": review_count,
                    })

                # Sort by task_order to get highest priority (lowest order number)
                sorted_tasks = sorted(todo_tasks, key=lambda t: t.get("task_order", 9999))
                next_task = sorted_tasks[0]

                # Mark as doing if requested
                if mark_as_doing:
                    update_response = await client.put(
                        urljoin(api_url, f"/api/tasks/{next_task['id']}"),
                        json={"status": "doing"},
                    )

                    if update_response.status_code == 200:
                        update_result = update_response.json()
                        next_task = update_result.get("task", next_task)

                # Get PRP context for the project
                prp_context = await _get_prp_context(project_id)

                # Get phase context if task is in a phase
                phase_context = await _get_phase_context(project_id, next_task.get("phase_id"))

                # Estimate task tokens
                token_estimate = _estimate_task_tokens(next_task)

                return json.dumps({
                    "success": True,
                    "task": next_task,
                    "resumed": False,
                    "message": f"Starting task: {next_task.get('title')}",
                    "remaining_count": len(todo_tasks) - 1,
                    "prp": prp_context,
                    "phase": phase_context,
                    "checkpoint": None,
                    "token_estimate": token_estimate,
                })

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(
                e, "get next task", {"project_id": project_id}
            )
        except Exception as e:
            logger.error(f"Error getting next task: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, "get next task")

    @mcp.tool()
    async def harness_complete(
        ctx: Context,
        task_id: str,
        commit_message: str | None = None,
        auto_commit: bool = False,
        auto_continue: bool = True,
        skip_tests: bool = False,
    ) -> str:
        """
        Mark a task as done and optionally commit changes to git.

        Also appends a timestamped entry to CHANGELOG.md under [Unreleased].
        By default, automatically retrieves the next task for continuous workflow.
        Optionally runs tests before completing - if tests fail, the task stays
        in "doing" status and must be fixed.

        Args:
            task_id: UUID of the task to complete
            commit_message: Optional custom commit message.
                           If not provided, generates one from task title.
            auto_commit: If True, stages all changes and creates a git commit
                        (default: False)
            auto_continue: If True (default), automatically gets the next task
                          and returns it in the response for continuous workflow.
            skip_tests: If True, skips test verification before completing.
                       Use when tests don't exist or aren't applicable.
                       (default: False)

        Returns:
            JSON with structure:
            - success: bool - Whether completion succeeded
            - task: dict - The completed task (or current task if tests failed)
            - tests: dict|null - Test verification results
              - passed: bool - Whether tests passed
              - output: str - Test output (truncated if long)
              - skipped: bool - Whether tests were skipped
            - commit: dict|null - Git commit info if auto_commit was True
              - hash: str - Commit hash
              - message: str - Commit message used
            - changelog: dict|null - Changelog entry info
              - entry: str - The entry that was added
              - section: str - Which section (Added/Changed/Fixed)
            - next_task: dict|null - The next task to work on (if auto_continue=True)
              - id: str - Task UUID
              - title: str - Task title
              - description: str - Task description
              - status: str - Task status (will be "doing" if marked)
            - remaining_count: int|null - Number of remaining todo tasks
            - all_complete: bool - True if no more tasks remain
            - error: str|null - Error message if failed

        Note:
            Git operations are performed in the current working directory.
            If not in a git repository, auto_commit will be skipped with a warning.

            If tests fail, the task remains in "doing" status and the response
            includes test output. The LLM should fix the issues and retry.
        """
        try:
            if not task_id:
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message="task_id is required",
                    suggestion="Provide a valid task UUID",
                )

            api_url = get_api_url()
            timeout = get_default_timeout()

            # Run tests before marking task as done (unless skipped)
            test_result = None
            if not skip_tests:
                test_result = await _run_test_verification()
                if test_result and not test_result.get("passed", True):
                    # Tests failed - return error without changing task status
                    return json.dumps({
                        "success": False,
                        "task": None,
                        "tests": test_result,
                        "error": "Tests failed. Fix the issues and try again.",
                        "message": "Task not completed - tests failed. The task remains in 'doing' status.",
                    })
            else:
                test_result = {"skipped": True, "passed": True}

            async with httpx.AsyncClient(timeout=timeout) as client:
                # Update task status to done
                response = await client.put(
                    urljoin(api_url, f"/api/tasks/{task_id}"),
                    json={"status": "done"},
                )

                if response.status_code == 404:
                    return MCPErrorFormatter.format_error(
                        error_type="not_found",
                        message=f"Task {task_id} not found",
                        suggestion="Verify the task_id is correct",
                        http_status=404,
                    )
                elif response.status_code != 200:
                    return MCPErrorFormatter.from_http_error(response, "complete task")

                result = response.json()
                task = result.get("task", {})

                # Handle git commit if requested
                commit_info = None
                if auto_commit:
                    commit_info = await _perform_git_commit(
                        task_title=task.get("title", "Task completed"),
                        commit_message=commit_message,
                        task_id=task_id,
                    )

                # Clear checkpoint for completed task
                checkpoint_cleared = False
                try:
                    await _manage_checkpoint(task_id=task_id, clear=True)
                    checkpoint_cleared = True
                except Exception as e:
                    logger.debug(f"Could not clear checkpoint for task {task_id}: {e}")

                # Append entry to CHANGELOG.md
                changelog_result = None
                try:
                    changelog_result = await _append_changelog_entry(
                        task_title=task.get("title", "Task completed"),
                        task_id=task_id,
                    )
                    if changelog_result.get("success"):
                        logger.info(f"Added changelog entry: {changelog_result.get('entry')}")
                    else:
                        logger.warning(f"Could not update changelog: {changelog_result.get('error')}")
                except Exception as e:
                    logger.debug(f"Could not update changelog for task {task_id}: {e}")

                # Auto-continue: Get next task if requested
                next_task_info = None
                remaining_count = None
                all_complete = False

                if auto_continue:
                    project_id = task.get("project_id")
                    if project_id:
                        next_task_result = await _get_next_task_for_project(
                            client, api_url, project_id, mark_as_doing=True
                        )
                        if next_task_result.get("success"):
                            next_task_info = next_task_result.get("task")
                            remaining_count = next_task_result.get("remaining_count", 0)
                            all_complete = next_task_info is None
                        else:
                            # No more tasks or error - mark as complete
                            all_complete = next_task_result.get("all_complete", True)
                            remaining_count = 0

                return json.dumps({
                    "success": True,
                    "task": task,
                    "tests": test_result,
                    "commit": commit_info,
                    "checkpoint_cleared": checkpoint_cleared,
                    "changelog": changelog_result,
                    "message": f"Task completed: {task.get('title')}",
                    "next_task": next_task_info,
                    "remaining_count": remaining_count,
                    "all_complete": all_complete,
                })

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(
                e, "complete task", {"task_id": task_id}
            )
        except Exception as e:
            logger.error(f"Error completing task: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, "complete task")

    @mcp.tool()
    async def harness_checkpoint(
        ctx: Context,
        task_id: str,
        step: int | None = None,
        files_modified: list[str] | None = None,
        next_action: str | None = None,
        notes: str | None = None,
        clear: bool = False,
    ) -> str:
        """
        Save or retrieve checkpoint data for task progress persistence.

        Checkpoints allow work to resume after context compaction by storing:
        - Current step in implementation
        - Files modified so far
        - Next action to take
        - Optional notes

        Args:
            task_id: UUID of the task to checkpoint
            step: Current step number in implementation (1-indexed)
            files_modified: List of file paths modified during this task
            next_action: Description of the next action to take
            notes: Optional notes about current state or blockers
            clear: If True, clears the checkpoint for this task

        Returns:
            JSON with structure:
            - success: bool - Whether checkpoint operation succeeded
            - checkpoint: dict|null - The checkpoint data (if exists)
            - message: str - Status message
            - file_path: str - Path to the checkpoint file

        Usage:
            Save checkpoint:
                harness_checkpoint(task_id="...", step=3, files_modified=["src/foo.py"],
                                  next_action="Add error handling")

            Get checkpoint (no other args):
                harness_checkpoint(task_id="...")

            Clear checkpoint:
                harness_checkpoint(task_id="...", clear=True)
        """
        try:
            if not task_id:
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message="task_id is required",
                    suggestion="Provide a valid task UUID",
                )

            checkpoint_result = await _manage_checkpoint(
                task_id=task_id,
                step=step,
                files_modified=files_modified,
                next_action=next_action,
                notes=notes,
                clear=clear,
            )

            return json.dumps(checkpoint_result)

        except Exception as e:
            logger.error(f"Error managing checkpoint: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, "manage checkpoint")

    @mcp.tool()
    async def phase_plan_context(
        ctx: Context,
        project_id: str,
    ) -> str:
        """
        Gather context for phase planning.

        This tool retrieves all the information needed to plan a new phase:
        - Project Requirements Plan (PRP) from RAG
        - CHANGELOG history (what's been done)
        - Existing phases and their status
        - Task summary by status

        Use this before creating a new phase with manage_phase and manage_task.

        Args:
            project_id: UUID of the project to plan for

        Returns:
            JSON with structure:
            - success: bool - Whether context was gathered
            - project: dict - Project details (title, description)
            - prp: dict|null - Project Requirements Plan
              - content: str - Full PRP text
              - source_id: str - RAG source identifier
            - changelog: dict - CHANGELOG content and recent entries
              - content: str - Full CHANGELOG text (truncated if long)
              - recent_entries: list - Recent entries from [Unreleased]
            - phases: list - Existing phases with status
            - task_summary: dict - Task counts by status
            - recommendation: str - Suggested next phase based on analysis

        Example workflow:
            1. Call phase_plan_context(project_id="...")
            2. Review PRP and CHANGELOG to understand project state
            3. Determine next logical phase
            4. Create phase with manage_phase("create", ...)
            5. Create tasks with manage_task("create", ...)
        """
        try:
            if not project_id:
                return MCPErrorFormatter.format_error(
                    error_type="validation_error",
                    message="project_id is required",
                    suggestion="Provide a valid project UUID",
                )

            api_url = get_api_url()
            timeout = get_default_timeout()

            result: dict = {
                "success": True,
                "project": None,
                "prp": None,
                "changelog": None,
                "phases": [],
                "task_summary": {},
                "recommendation": None,
            }

            async with httpx.AsyncClient(timeout=timeout) as client:
                # Get project details
                project_response = await client.get(
                    urljoin(api_url, f"/api/projects/{project_id}")
                )

                if project_response.status_code == 404:
                    return MCPErrorFormatter.format_error(
                        error_type="not_found",
                        message=f"Project {project_id} not found",
                        suggestion="Verify the project_id is correct",
                        http_status=404,
                    )
                elif project_response.status_code == 200:
                    project_data = project_response.json()
                    result["project"] = {
                        "id": project_data.get("id"),
                        "title": project_data.get("title"),
                        "description": project_data.get("description"),
                    }

                # Get PRP from RAG
                prp_context = await _get_prp_context(project_id)
                if prp_context:
                    result["prp"] = prp_context

                # Get existing phases
                phases_response = await client.get(
                    urljoin(api_url, f"/api/projects/{project_id}/phases"),
                    params={"per_page": 100},
                )
                if phases_response.status_code == 200:
                    phases_data = phases_response.json()
                    phases = phases_data.get("phases", [])
                    result["phases"] = [
                        {
                            "id": p.get("id"),
                            "phase_number": p.get("phase_number"),
                            "title": p.get("title"),
                            "status": p.get("status"),
                            "summary": p.get("summary"),
                        }
                        for p in phases
                    ]

                # Get task summary
                task_counts = {"todo": 0, "doing": 0, "review": 0, "done": 0}
                for status in task_counts.keys():
                    status_response = await client.get(
                        urljoin(api_url, "/api/tasks"),
                        params={
                            "project_id": project_id,
                            "status": status,
                            "per_page": 1,
                            "include_closed": True,
                        },
                    )
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        task_counts[status] = status_data.get("total_count", 0)

                result["task_summary"] = task_counts

            # Read CHANGELOG
            changelog_result = await _read_changelog_for_context()
            if changelog_result.get("success"):
                result["changelog"] = changelog_result

            # Generate recommendation
            result["recommendation"] = _generate_phase_recommendation(result)

            return json.dumps(result)

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(
                e, "get phase plan context", {"project_id": project_id}
            )
        except Exception as e:
            logger.error(f"Error getting phase plan context: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, "get phase plan context")

    logger.info("Harness tools registered (project_initialize, harness_initialize, harness_next_task, harness_complete, harness_checkpoint, phase_plan_context)")


def _parse_specification(specification: str) -> list[dict]:
    """
    Parse a specification string into task items.

    Handles various formats:
    - Numbered lists: "1. Task one\\n2. Task two"
    - Bullet lists: "- Task one\\n- Task two" or "* Task one"
    - Plain text: "Task one. Task two. Task three."

    Returns:
        List of dicts with 'title' and optional 'description' keys
    """
    tasks = []
    lines = specification.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove common list prefixes
        # Numbered: "1.", "1)", "1:"
        # Bullets: "-", "*", "+"
        import re
        cleaned = re.sub(r"^(\d+[\.\)\:]|\-|\*|\+)\s*", "", line)
        cleaned = cleaned.strip()

        if cleaned:
            # Split on sentence-ending punctuation if line is long
            if len(cleaned) > 100 and ". " in cleaned:
                # Might be multiple tasks in one line
                sentences = re.split(r"\.\s+", cleaned)
                for sentence in sentences:
                    sentence = sentence.strip().rstrip(".")
                    if sentence and len(sentence) > 5:  # Skip very short fragments
                        tasks.append({"title": sentence})
            else:
                tasks.append({"title": cleaned.rstrip(".")})

    return tasks


async def _get_todo_count(client: httpx.AsyncClient, api_url: str, project_id: str) -> int:
    """Get count of remaining todo tasks for a project."""
    try:
        response = await client.get(
            urljoin(api_url, "/api/tasks"),
            params={
                "project_id": project_id,
                "status": "todo",
                "per_page": 1,
            },
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("total_count", 0)
    except Exception:
        pass
    return 0


async def _get_next_task_for_project(
    client: httpx.AsyncClient,
    api_url: str,
    project_id: str,
    mark_as_doing: bool = True,
) -> dict:
    """
    Get the next task for a project (internal helper for auto-continue).

    This is a simplified version of harness_next_task for internal use.

    Args:
        client: httpx AsyncClient instance
        api_url: Base API URL
        project_id: UUID of the project
        mark_as_doing: If True, marks the task as "doing"

    Returns:
        dict with:
        - success: bool
        - task: dict|null - The next task
        - remaining_count: int - Number of remaining todo tasks
        - all_complete: bool - True if no more tasks
    """
    try:
        # First check for any task already in "doing" status
        doing_response = await client.get(
            urljoin(api_url, "/api/tasks"),
            params={
                "project_id": project_id,
                "status": "doing",
                "per_page": 1,
            },
        )

        if doing_response.status_code == 200:
            doing_result = doing_response.json()
            doing_tasks = doing_result.get("tasks", [])

            if doing_tasks:
                # Return existing in-progress task
                task = doing_tasks[0]
                todo_count = await _get_todo_count(client, api_url, project_id)
                return {
                    "success": True,
                    "task": task,
                    "remaining_count": todo_count,
                    "all_complete": False,
                    "resumed": True,
                }

        # No doing task, get next todo task
        todo_response = await client.get(
            urljoin(api_url, "/api/tasks"),
            params={
                "project_id": project_id,
                "status": "todo",
                "per_page": 100,
                "include_closed": False,
            },
        )

        if todo_response.status_code != 200:
            return {
                "success": False,
                "task": None,
                "remaining_count": 0,
                "all_complete": True,
                "error": f"HTTP {todo_response.status_code}",
            }

        todo_result = todo_response.json()
        todo_tasks = todo_result.get("tasks", [])

        if not todo_tasks:
            return {
                "success": True,
                "task": None,
                "remaining_count": 0,
                "all_complete": True,
            }

        # Sort by task_order to get highest priority (lowest order number)
        sorted_tasks = sorted(todo_tasks, key=lambda t: t.get("task_order", 9999))
        next_task = sorted_tasks[0]

        # Mark as doing if requested
        if mark_as_doing:
            update_response = await client.put(
                urljoin(api_url, f"/api/tasks/{next_task['id']}"),
                json={"status": "doing"},
            )

            if update_response.status_code == 200:
                update_result = update_response.json()
                next_task = update_result.get("task", next_task)

        return {
            "success": True,
            "task": next_task,
            "remaining_count": len(todo_tasks) - 1,
            "all_complete": False,
            "resumed": False,
        }

    except Exception as e:
        logger.error(f"Error getting next task for project {project_id}: {e}")
        return {
            "success": False,
            "task": None,
            "remaining_count": 0,
            "all_complete": True,
            "error": str(e),
        }


async def _run_test_verification() -> dict:
    """
    Run test verification before marking a task as complete.

    Detects the test framework and runs appropriate tests.
    Returns a dict with test results.

    Returns:
        dict with:
        - passed: bool - Whether tests passed
        - output: str - Test output (truncated if long)
        - framework: str - Detected test framework
        - skipped: bool - Whether tests were skipped (no framework found)
        - error: str|null - Error message if something went wrong
    """
    import asyncio
    import os
    from pathlib import Path

    # Determine repo root
    try:
        process = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--show-toplevel",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
        if process.returncode == 0:
            repo_root = Path(stdout.decode().strip())
        else:
            repo_root = Path.cwd()
    except Exception:
        repo_root = Path.cwd()

    # Detect test framework and build command
    test_cmd = None
    framework = None

    # Check for Python pytest
    if (repo_root / "pytest.ini").exists() or \
       (repo_root / "pyproject.toml").exists() or \
       (repo_root / "tests").exists() or \
       (repo_root / "python" / "tests").exists():
        # Check if pytest is available
        try:
            proc = await asyncio.create_subprocess_exec(
                "which", "pytest",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=5)
            if proc.returncode == 0:
                test_cmd = ["pytest", "-v", "--tb=short", "-x"]  # Stop on first failure
                framework = "pytest"
        except Exception:
            pass

    # Check for Node.js test frameworks (if no Python tests found)
    if not test_cmd:
        package_json_paths = [
            repo_root / "package.json",
            repo_root / "archon-ui-main" / "package.json",
        ]
        for pkg_path in package_json_paths:
            if pkg_path.exists():
                try:
                    import json as json_module
                    with open(pkg_path, "r") as f:
                        pkg = json_module.load(f)
                    scripts = pkg.get("scripts", {})
                    if "test" in scripts:
                        test_cmd = ["npm", "test", "--", "--run"]  # --run for non-watch mode
                        framework = "npm/vitest"
                        break
                except Exception:
                    pass

    # No test framework detected
    if not test_cmd:
        logger.info("No test framework detected, skipping test verification")
        return {
            "passed": True,
            "skipped": True,
            "output": "No test framework detected. Tests skipped.",
            "framework": None,
        }

    # Run tests
    try:
        logger.info(f"Running tests with {framework}: {' '.join(test_cmd)}")
        process = await asyncio.create_subprocess_exec(
            *test_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(repo_root),
        )

        # Wait for completion with timeout (5 minutes max)
        stdout, _ = await asyncio.wait_for(
            process.communicate(),
            timeout=300,
        )

        output = stdout.decode() if stdout else ""

        # Truncate output if too long (keep first and last parts)
        max_output_length = 5000
        if len(output) > max_output_length:
            half = max_output_length // 2
            output = output[:half] + "\n\n... (output truncated) ...\n\n" + output[-half:]

        passed = process.returncode == 0

        logger.info(f"Tests {'passed' if passed else 'failed'} (exit code: {process.returncode})")

        return {
            "passed": passed,
            "output": output,
            "framework": framework,
            "skipped": False,
            "exit_code": process.returncode,
        }

    except asyncio.TimeoutError:
        logger.error("Test execution timed out after 5 minutes")
        return {
            "passed": False,
            "output": "Test execution timed out after 5 minutes",
            "framework": framework,
            "skipped": False,
            "error": "Timeout",
        }
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return {
            "passed": False,
            "output": str(e),
            "framework": framework,
            "skipped": False,
            "error": str(e),
        }


async def _get_prp_context(project_id: str) -> dict | None:
    """
    Get PRP (Project Requirements Plan) context for a project.

    Retrieves the stored PRP from RAG to provide context for task implementation.

    Args:
        project_id: UUID of the project

    Returns:
        dict with PRP content and metadata, or None if not found
    """
    try:
        from src.mcp_server.features.harness.prp_storage import retrieve_prp_for_project

        result = await retrieve_prp_for_project(project_id)

        if result.get("success"):
            return {
                "content": result.get("content", ""),
                "source_id": result.get("source_id"),
                "url": result.get("url"),
            }
        else:
            logger.debug(f"No PRP found for project {project_id}: {result.get('error')}")
            return None

    except Exception as e:
        logger.debug(f"Error retrieving PRP for project {project_id}: {e}")
        return None


async def _get_phase_context(project_id: str, phase_id: str | None) -> dict | None:
    """
    Get phase context for a task.

    Args:
        project_id: UUID of the project
        phase_id: UUID of the phase (from task)

    Returns:
        dict with phase details, or None if no phase
    """
    if not phase_id:
        return None

    try:
        api_url = get_api_url()
        timeout = get_default_timeout()

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                urljoin(api_url, f"/api/projects/{project_id}/phases/{phase_id}")
            )

            if response.status_code == 200:
                result = response.json()
                phase = result.get("phase", result)
                return {
                    "id": phase.get("id"),
                    "phase_number": phase.get("phase_number"),
                    "title": phase.get("title"),
                    "description": phase.get("description"),
                    "status": phase.get("status"),
                    "goals": phase.get("goals", []),
                }
            else:
                logger.debug(f"Could not retrieve phase {phase_id}: {response.status_code}")
                return None

    except Exception as e:
        logger.debug(f"Error retrieving phase {phase_id}: {e}")
        return None


async def _get_active_phase_for_project(project_id: str) -> dict | None:
    """
    Get the currently active phase for a project.

    Args:
        project_id: UUID of the project

    Returns:
        dict with active phase details, or None if no active phase
    """
    try:
        api_url = get_api_url()
        timeout = get_default_timeout()

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                urljoin(api_url, f"/api/projects/{project_id}/phases/active")
            )

            if response.status_code == 200:
                result = response.json()
                phase = result.get("phase")
                if phase:
                    return {
                        "id": phase.get("id"),
                        "phase_number": phase.get("phase_number"),
                        "title": phase.get("title"),
                        "description": phase.get("description"),
                        "status": phase.get("status"),
                        "goals": phase.get("goals", []),
                    }
            return None

    except Exception as e:
        logger.debug(f"Error retrieving active phase for project {project_id}: {e}")
        return None


async def _run_git_command(
    args: list[str],
    timeout_seconds: int,
    cwd: str | None = None,
) -> tuple[int, str, str]:
    """
    Run a git command asynchronously with timeout.

    Args:
        args: Command arguments (e.g., ["git", "status"])
        timeout_seconds: Timeout in seconds
        cwd: Working directory (optional)

    Returns:
        Tuple of (return_code, stdout, stderr)

    Raises:
        asyncio.TimeoutError: If command times out
    """
    import asyncio

    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout_seconds,
        )
        return process.returncode or 0, stdout.decode(), stderr.decode()
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise


async def _run_remote_git_command(
    git_args: list[str],
    config: "GitConfig",
) -> tuple[int, str, str]:
    """
    Run a git command on a remote server via SSH.

    Args:
        git_args: Git command arguments (e.g., ["add", "-A"])
        config: Git configuration with remote settings

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    import asyncio
    import shlex

    # Build the remote command
    git_cmd = " ".join(shlex.quote(arg) for arg in ["git"] + git_args)
    remote_cmd = f"cd {shlex.quote(config.remote_path)} && {git_cmd}"

    ssh_args = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        config.ssh_target,
        remote_cmd,
    ]

    return await _run_git_command(ssh_args, config.timeout_seconds)


async def _perform_git_commit(
    task_title: str,
    commit_message: str | None,
    task_id: str,
) -> dict | None:
    """
    Perform git add and commit operations.

    Supports two execution modes based on GIT_EXECUTION_MODE env var:
    - local: Run git commands directly (default)
    - remote: Run git commands via SSH on a remote server

    Remote mode is useful when working over SSHFS where local git
    operations can be slow or unreliable.

    Environment variables for remote mode:
        GIT_EXECUTION_MODE=remote
        GIT_REMOTE_HOST=hostname
        GIT_REMOTE_USER=username
        GIT_REMOTE_PATH=/path/to/repo
        GIT_OPERATION_TIMEOUT=60

    Returns:
        dict with commit info or skip reason
    """
    import asyncio

    from src.mcp_server.utils.git_config import GitConfig, get_git_config

    try:
        config = get_git_config()
    except ValueError as e:
        logger.error(f"Git config error: {e}")
        return {"skipped": True, "reason": f"Configuration error: {e}"}

    async def run_git(args: list[str]) -> tuple[int, str, str]:
        """Run git command using configured mode."""
        if config.is_remote:
            return await _run_remote_git_command(args, config)
        else:
            return await _run_git_command(
                ["git"] + args,
                config.timeout_seconds,
                cwd=config.local_repo_path,  # Use configured repo path
            )

    try:
        # Check if we're in a git repository
        returncode, stdout, stderr = await run_git(["rev-parse", "--git-dir"])

        if returncode != 0:
            logger.warning("Not in a git repository, skipping commit")
            return {"skipped": True, "reason": "Not a git repository"}

        # Stage all changes
        returncode, stdout, stderr = await run_git(["add", "-A"])

        if returncode != 0:
            return {"skipped": True, "reason": f"Git add failed: {stderr}"}

        # Check if there are changes to commit
        returncode, stdout, stderr = await run_git(["status", "--porcelain"])

        if not stdout.strip():
            return {"skipped": True, "reason": "No changes to commit"}

        # Generate commit message
        if not commit_message:
            commit_message = f"feat: {task_title}\n\nTask-ID: {task_id}"

        # Create commit
        returncode, stdout, stderr = await run_git(["commit", "-m", commit_message])

        if returncode != 0:
            return {"skipped": True, "reason": f"Git commit failed: {stderr}"}

        # Get commit hash
        returncode, stdout, stderr = await run_git(["rev-parse", "--short", "HEAD"])

        commit_hash = stdout.strip() if returncode == 0 else "unknown"

        return {
            "hash": commit_hash,
            "message": commit_message,
            "skipped": False,
            "mode": config.mode.value,
        }

    except asyncio.TimeoutError:
        timeout = config.timeout_seconds
        logger.error(f"Git operation timed out after {timeout}s")
        return {
            "skipped": True,
            "reason": f"Git operation timed out after {timeout} seconds",
        }
    except Exception as e:
        logger.error(f"Git commit error: {e}")
        return {"skipped": True, "reason": str(e)}


async def _manage_checkpoint(
    task_id: str,
    step: int | None = None,
    files_modified: list[str] | None = None,
    next_action: str | None = None,
    notes: str | None = None,
    clear: bool = False,
) -> dict:
    """
    Manage checkpoint data for a task.

    Checkpoints are stored in .harness/checkpoint.json in the repository root.

    Args:
        task_id: UUID of the task
        step: Current step number
        files_modified: List of modified file paths
        next_action: Description of next action
        notes: Optional notes
        clear: If True, removes checkpoint for this task

    Returns:
        dict with operation result
    """
    import os
    from datetime import datetime, timezone
    from pathlib import Path

    # Determine checkpoint file location
    # Try to find repo root via git, fallback to cwd
    try:
        import asyncio

        process = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--show-toplevel",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
        if process.returncode == 0:
            repo_root = Path(stdout.decode().strip())
        else:
            repo_root = Path.cwd()
    except Exception:
        repo_root = Path.cwd()

    harness_dir = repo_root / ".harness"
    checkpoint_file = harness_dir / "checkpoint.json"

    # Load existing checkpoints
    checkpoints = {}
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, "r") as f:
                checkpoints = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not read checkpoint file: {e}")
            checkpoints = {}

    # Handle clear operation
    if clear:
        if task_id in checkpoints:
            del checkpoints[task_id]
            # Write back
            harness_dir.mkdir(parents=True, exist_ok=True)
            with open(checkpoint_file, "w") as f:
                json.dump(checkpoints, f, indent=2)

            return {
                "success": True,
                "checkpoint": None,
                "message": f"Checkpoint cleared for task {task_id}",
                "file_path": str(checkpoint_file),
            }
        else:
            return {
                "success": True,
                "checkpoint": None,
                "message": f"No checkpoint found for task {task_id}",
                "file_path": str(checkpoint_file),
            }

    # Check if this is a read-only request (only task_id provided)
    is_read_only = (
        step is None and
        files_modified is None and
        next_action is None and
        notes is None
    )

    if is_read_only:
        # Return existing checkpoint if it exists
        existing = checkpoints.get(task_id)
        if existing:
            return {
                "success": True,
                "checkpoint": existing,
                "message": f"Checkpoint found for task {task_id}",
                "file_path": str(checkpoint_file),
            }
        else:
            return {
                "success": True,
                "checkpoint": None,
                "message": f"No checkpoint found for task {task_id}",
                "file_path": str(checkpoint_file),
            }

    # Save/update checkpoint
    existing_checkpoint = checkpoints.get(task_id, {})

    # Build updated checkpoint, merging with existing data
    updated_checkpoint = {
        "task_id": task_id,
        "step": step if step is not None else existing_checkpoint.get("step"),
        "files_modified": files_modified if files_modified is not None else existing_checkpoint.get("files_modified", []),
        "next_action": next_action if next_action is not None else existing_checkpoint.get("next_action"),
        "notes": notes if notes is not None else existing_checkpoint.get("notes"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "created_at": existing_checkpoint.get("created_at", datetime.now(timezone.utc).isoformat()),
    }

    # Remove None values for cleaner JSON
    updated_checkpoint = {k: v for k, v in updated_checkpoint.items() if v is not None}

    checkpoints[task_id] = updated_checkpoint

    # Ensure directory exists and write file
    harness_dir.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoints, f, indent=2)

    # Also add .harness to .gitignore if it doesn't exist
    gitignore_path = repo_root / ".gitignore"
    harness_pattern = ".harness/"
    try:
        if gitignore_path.exists():
            with open(gitignore_path, "r") as f:
                gitignore_content = f.read()
            if harness_pattern not in gitignore_content:
                with open(gitignore_path, "a") as f:
                    f.write(f"\n# Harness checkpoint files\n{harness_pattern}\n")
                logger.info("Added .harness/ to .gitignore")
        else:
            with open(gitignore_path, "w") as f:
                f.write(f"# Harness checkpoint files\n{harness_pattern}\n")
            logger.info("Created .gitignore with .harness/")
    except IOError as e:
        logger.warning(f"Could not update .gitignore: {e}")

    return {
        "success": True,
        "checkpoint": updated_checkpoint,
        "message": f"Checkpoint saved for task {task_id}",
        "file_path": str(checkpoint_file),
    }


async def _get_checkpoint_for_task(task_id: str) -> dict | None:
    """
    Get checkpoint data for a task if it exists.

    This is used by harness_next_task to include checkpoint in response.

    Args:
        task_id: UUID of the task

    Returns:
        Checkpoint data dict or None
    """
    try:
        result = await _manage_checkpoint(task_id=task_id)
        if result.get("success") and result.get("checkpoint"):
            return result["checkpoint"]
        return None
    except Exception as e:
        logger.debug(f"Error retrieving checkpoint for task {task_id}: {e}")
        return None


async def _append_changelog_entry(
    task_title: str,
    task_id: str,
    entry_type: str = "Added",
) -> dict:
    """
    Append an entry to CHANGELOG.md under the [Unreleased] section.

    Args:
        task_title: Title of the completed task
        task_id: UUID of the task (for traceability)
        entry_type: One of "Added", "Changed", "Fixed" (default: "Added")

    Returns:
        dict with success status and details
    """
    import re
    from datetime import datetime, timezone
    from pathlib import Path

    # Validate entry type
    valid_types = ["Added", "Changed", "Fixed"]
    if entry_type not in valid_types:
        entry_type = "Added"

    # Determine changelog file location (repo root)
    try:
        import asyncio

        process = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--show-toplevel",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
        if process.returncode == 0:
            repo_root = Path(stdout.decode().strip())
        else:
            repo_root = Path.cwd()
    except Exception:
        repo_root = Path.cwd()

    changelog_path = repo_root / "CHANGELOG.md"

    if not changelog_path.exists():
        return {
            "success": False,
            "error": "CHANGELOG.md not found",
            "file_path": str(changelog_path),
        }

    try:
        # Read existing content
        with open(changelog_path, "r") as f:
            content = f.read()

        # Generate timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        # Format the entry
        # Extract type and scope from task title if it follows convention
        # e.g., "feat(harness): add checkpoint" -> "harness", "add checkpoint"
        commit_match = re.match(r"^(feat|fix|docs|refactor|test|chore)\((\w+)\):\s*(.+)$", task_title, re.IGNORECASE)
        if commit_match:
            commit_type, scope, description = commit_match.groups()
            # Map commit types to changelog sections
            type_mapping = {
                "feat": "Added",
                "fix": "Fixed",
                "docs": "Added",
                "refactor": "Changed",
                "test": "Added",
                "chore": "Changed",
            }
            entry_type = type_mapping.get(commit_type.lower(), entry_type)
            entry_text = f"- **{timestamp}** - {commit_type}({scope}): {description} (Task: {task_id[:8]})"
        else:
            # Use title as-is
            entry_text = f"- **{timestamp}** - {task_title} (Task: {task_id[:8]})"

        # Find the correct section under [Unreleased]
        # Pattern: ## [Unreleased] ... ### <entry_type>
        unreleased_pattern = r"(## \[Unreleased\].*?)(### " + entry_type + r"\n)"
        unreleased_match = re.search(unreleased_pattern, content, re.DOTALL)

        if unreleased_match:
            # Insert after the ### <entry_type> header
            insert_pos = unreleased_match.end()
            new_content = content[:insert_pos] + entry_text + "\n" + content[insert_pos:]
        else:
            # Section doesn't exist under Unreleased, try to add it
            unreleased_header = re.search(r"(## \[Unreleased\]\n)", content)
            if unreleased_header:
                # Find the next section after [Unreleased]
                next_section = re.search(r"\n(### \w+)", content[unreleased_header.end():])
                if next_section:
                    # Insert new section before existing sections
                    insert_pos = unreleased_header.end() + next_section.start()
                    new_section = f"\n### {entry_type}\n{entry_text}\n"
                    new_content = content[:insert_pos] + new_section + content[insert_pos:]
                else:
                    # No sections yet, add after [Unreleased]
                    insert_pos = unreleased_header.end()
                    new_section = f"\n### {entry_type}\n{entry_text}\n"
                    new_content = content[:insert_pos] + new_section + content[insert_pos:]
            else:
                # No [Unreleased] section, can't update
                return {
                    "success": False,
                    "error": "[Unreleased] section not found in CHANGELOG.md",
                    "file_path": str(changelog_path),
                }

        # Write updated content
        with open(changelog_path, "w") as f:
            f.write(new_content)

        return {
            "success": True,
            "entry": entry_text,
            "section": entry_type,
            "file_path": str(changelog_path),
        }

    except Exception as e:
        logger.error(f"Error updating CHANGELOG.md: {e}")
        return {
            "success": False,
            "error": str(e),
            "file_path": str(changelog_path),
        }


def _estimate_task_tokens(task: dict) -> dict:
    """
    Estimate the number of tokens a task will consume.

    Uses heuristics based on task title and description to predict
    token usage and warn about potential context compaction.

    Args:
        task: Task dictionary with title, description, etc.

    Returns:
        dict with:
        - estimated_tokens: int - Estimated token count
        - warning: str|null - Warning message if task is large
        - breakdown: dict - Token breakdown by category
        - risk_level: str - "low", "medium", or "high"
    """
    import re

    title = task.get("title", "").lower()
    description = task.get("description", "").lower()
    full_text = f"{title} {description}"

    # Base tokens for task overhead
    base_tokens = 500

    # Estimate based on description length (roughly 4 chars per token)
    description_tokens = len(task.get("description", "")) // 4

    # Keywords that suggest larger tasks
    keyword_costs = {
        "implement": 3000,
        "create": 2500,
        "refactor": 4000,
        "test": 2500,
        "add": 2000,
        "update": 1500,
        "fix": 1500,
        "migrate": 3500,
        "integrate": 3000,
        "configure": 1500,
        "setup": 2000,
        "design": 1000,
        "document": 1000,
    }

    keyword_tokens = 0
    matched_keywords = []
    for keyword, cost in keyword_costs.items():
        if keyword in title:
            keyword_tokens += cost
            matched_keywords.append(keyword)

    # File-related estimates
    file_patterns = [
        r"files?\s+to\s+(create|modify|update)",
        r"create\s+.*\.py",
        r"modify\s+.*\.py",
        r"update\s+.*\.ts",
    ]
    files_mentioned = 0
    for pattern in file_patterns:
        files_mentioned += len(re.findall(pattern, full_text))

    file_tokens = files_mentioned * 1500

    # Check for multi-step indicators
    step_indicators = re.findall(r"^\s*\d+\.|^-\s|\[\s*\]", description, re.MULTILINE)
    step_tokens = len(step_indicators) * 500

    # Total estimate
    total_tokens = base_tokens + description_tokens + keyword_tokens + file_tokens + step_tokens

    # Determine risk level and warning
    SAFE_THRESHOLD = 8000
    WARNING_THRESHOLD = 15000
    CRITICAL_THRESHOLD = 25000

    if total_tokens < SAFE_THRESHOLD:
        risk_level = "low"
        warning = None
    elif total_tokens < WARNING_THRESHOLD:
        risk_level = "medium"
        warning = f"Task may be moderately large (~{total_tokens:,} tokens). Consider saving checkpoints."
    elif total_tokens < CRITICAL_THRESHOLD:
        risk_level = "high"
        warning = f"Large task (~{total_tokens:,} tokens). High risk of context compaction. Consider breaking into smaller tasks."
    else:
        risk_level = "critical"
        warning = f"Very large task (~{total_tokens:,} tokens). Strongly recommend splitting into smaller sub-tasks."

    return {
        "estimated_tokens": total_tokens,
        "warning": warning,
        "risk_level": risk_level,
        "breakdown": {
            "base": base_tokens,
            "description": description_tokens,
            "keywords": keyword_tokens,
            "files": file_tokens,
            "steps": step_tokens,
        },
        "matched_keywords": matched_keywords,
        "thresholds": {
            "safe": SAFE_THRESHOLD,
            "warning": WARNING_THRESHOLD,
            "critical": CRITICAL_THRESHOLD,
        },
    }


async def _read_changelog_for_context() -> dict:
    """
    Read CHANGELOG.md and extract relevant context for phase planning.

    Returns:
        dict with:
        - success: bool
        - content: str - Truncated CHANGELOG content
        - recent_entries: list - Entries from [Unreleased] section
        - file_path: str - Path to CHANGELOG.md
        - error: str|null - Error message if failed
    """
    import re
    from pathlib import Path

    # Find repo root
    try:
        import asyncio

        process = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--show-toplevel",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
        if process.returncode == 0:
            repo_root = Path(stdout.decode().strip())
        else:
            repo_root = Path.cwd()
    except Exception:
        repo_root = Path.cwd()

    changelog_path = repo_root / "CHANGELOG.md"

    if not changelog_path.exists():
        return {
            "success": False,
            "content": None,
            "recent_entries": [],
            "file_path": str(changelog_path),
            "error": "CHANGELOG.md not found",
        }

    try:
        with open(changelog_path, "r") as f:
            content = f.read()

        # Extract recent entries from [Unreleased] section
        recent_entries = []
        unreleased_match = re.search(
            r"## \[Unreleased\](.*?)(?=\n## \[|$)",
            content,
            re.DOTALL
        )

        if unreleased_match:
            unreleased_content = unreleased_match.group(1)
            # Find all bullet points with timestamps
            entry_pattern = r"- \*\*(\d{4}-\d{2}-\d{2}[^*]*)\*\* - ([^\n]+)"
            for match in re.finditer(entry_pattern, unreleased_content):
                recent_entries.append({
                    "timestamp": match.group(1).strip(),
                    "entry": match.group(2).strip(),
                })

        # Truncate content if too long (keep first 3000 chars)
        max_length = 3000
        truncated_content = content[:max_length]
        if len(content) > max_length:
            truncated_content += f"\n\n... (truncated, {len(content)} total chars)"

        return {
            "success": True,
            "content": truncated_content,
            "recent_entries": recent_entries[:10],  # Last 10 entries
            "file_path": str(changelog_path),
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "content": None,
            "recent_entries": [],
            "file_path": str(changelog_path),
            "error": str(e),
        }


def _generate_phase_recommendation(context: dict) -> str:
    """
    Generate a recommendation for the next phase based on context.

    Args:
        context: The gathered context including PRP, phases, tasks

    Returns:
        str: A recommendation string
    """
    phases = context.get("phases", [])
    task_summary = context.get("task_summary", {})
    prp = context.get("prp")

    # Check if there are active phases
    active_phases = [p for p in phases if p.get("status") == "active"]
    planning_phases = [p for p in phases if p.get("status") == "planning"]
    completed_phases = [p for p in phases if p.get("status") == "complete"]

    # Check task counts
    todo_count = task_summary.get("todo", 0)
    doing_count = task_summary.get("doing", 0)
    done_count = task_summary.get("done", 0)

    # Generate recommendation
    if not prp:
        return "No PRP found. Consider running /project-new to create a project with a PRP first."

    if active_phases:
        active_phase = active_phases[0]
        if todo_count > 0 or doing_count > 0:
            return f"Active phase '{active_phase.get('title')}' has {todo_count} todo and {doing_count} in-progress tasks. Complete current phase before planning next."
        else:
            return f"Active phase '{active_phase.get('title')}' appears complete (no remaining tasks). Consider running /phase-done to summarize and close it."

    if planning_phases:
        return f"Phase '{planning_phases[0].get('title')}' is in planning status. Activate it or delete to plan a new phase."

    if not phases:
        return "No phases exist. Create the first phase based on the PRP's initial goals."

    if completed_phases:
        last_phase = max(completed_phases, key=lambda p: p.get("phase_number", 0))
        next_num = last_phase.get("phase_number", 0) + 1
        return f"Phase {last_phase.get('phase_number')} '{last_phase.get('title')}' is complete. Ready to create Phase {next_num} based on remaining PRP goals."

    return "Review the PRP and CHANGELOG to determine the next logical phase."

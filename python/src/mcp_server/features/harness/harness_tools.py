"""
Harness tools for Archon MCP Server.

This module provides tools for task automation workflows:
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
            - checkpoint: dict|null - Saved progress for resumed tasks
              - step: int - Current step number
              - files_modified: list - Files changed so far
              - next_action: str - What to do next
              - timestamp: str - When checkpoint was saved

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

                        return json.dumps({
                            "success": True,
                            "task": task,
                            "resumed": True,
                            "message": f"Resuming in-progress task: {task.get('title')}",
                            "remaining_count": todo_count,
                            "prp": prp_context,
                            "checkpoint": checkpoint,
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

                return json.dumps({
                    "success": True,
                    "task": next_task,
                    "resumed": False,
                    "message": f"Starting task: {next_task.get('title')}",
                    "remaining_count": len(todo_tasks) - 1,
                    "prp": prp_context,
                    "checkpoint": None,
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
    ) -> str:
        """
        Mark a task as done and optionally commit changes to git.

        Args:
            task_id: UUID of the task to complete
            commit_message: Optional custom commit message.
                           If not provided, generates one from task title.
            auto_commit: If True, stages all changes and creates a git commit
                        (default: False)

        Returns:
            JSON with structure:
            - success: bool - Whether completion succeeded
            - task: dict - The completed task
            - commit: dict|null - Git commit info if auto_commit was True
              - hash: str - Commit hash
              - message: str - Commit message used
            - error: str|null - Error message if failed

        Note:
            Git operations are performed in the current working directory.
            If not in a git repository, auto_commit will be skipped with a warning.
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

                return json.dumps({
                    "success": True,
                    "task": task,
                    "commit": commit_info,
                    "checkpoint_cleared": checkpoint_cleared,
                    "message": f"Task completed: {task.get('title')}",
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

    logger.info("Harness tools registered")


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

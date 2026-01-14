"""
Harness tools for Archon MCP Server.

This module provides tools for task automation workflows:
- harness_initialize: Parse specs and create tasks automatically
- harness_next_task: Get next todo task with smart selection
- harness_complete: Mark task done and optionally commit to git

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
            - error: str|null - Error message if failed

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
                # First verify project exists
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

            return json.dumps({
                "success": len(created_tasks) > 0,
                "tasks_created": len(created_tasks),
                "tasks": created_tasks,
                "errors": errors if errors else None,
                "project_id": project_id,
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

                        return json.dumps({
                            "success": True,
                            "task": task,
                            "resumed": True,
                            "message": f"Resuming in-progress task: {task.get('title')}",
                            "remaining_count": todo_count,
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

                return json.dumps({
                    "success": True,
                    "task": next_task,
                    "resumed": False,
                    "message": f"Starting task: {next_task.get('title')}",
                    "remaining_count": len(todo_tasks) - 1,
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

                return json.dumps({
                    "success": True,
                    "task": task,
                    "commit": commit_info,
                    "message": f"Task completed: {task.get('title')}",
                })

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(
                e, "complete task", {"task_id": task_id}
            )
        except Exception as e:
            logger.error(f"Error completing task: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, "complete task")

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

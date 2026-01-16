"""
Phase management tools for Archon MCP Server.

This module provides consolidated phase management tools:
- find_phases: List, search, and get individual phases
- manage_phase: Create, update, delete, activate, and complete phases
"""

import json
import logging
from typing import Any
from urllib.parse import urljoin

import httpx
from mcp.server.fastmcp import Context, FastMCP

from src.mcp_server.utils.error_handling import MCPErrorFormatter
from src.mcp_server.utils.timeout_config import get_default_timeout
from src.server.config.service_discovery import get_api_url

logger = logging.getLogger(__name__)

# Optimization constants
DEFAULT_PAGE_SIZE = 10


def register_phase_tools(mcp: FastMCP):
    """Register phase management tools with the MCP server."""

    @mcp.tool()
    async def find_phases(
        ctx: Context,
        project_id: str,
        phase_id: str | None = None,
        status: str | None = None,
        include_tasks: bool = False,
        page: int = 1,
        per_page: int = DEFAULT_PAGE_SIZE,
    ) -> str:
        """
        Find and list phases for a project.

        Phases represent distinct stages in a project lifecycle (e.g., Setup,
        Implementation, Testing, Documentation). Tasks can be assigned to phases
        for better organization.

        Args:
            project_id: Project UUID (required)
            phase_id: Get specific phase by ID (returns full details with tasks)
            status: Filter by status ("planning", "active", "complete")
            include_tasks: If True, includes task counts for each phase
            page: Page number for pagination
            per_page: Items per page (default: 10)

        Returns:
            JSON with structure:
            - success: bool - Operation success status
            - phases: list[dict] - Array of phases (if listing)
            - phase: dict - Single phase (if phase_id provided)
            - total_count: int - Total number of phases

        Phase Status Flow:
            planning -> active -> complete

        Examples:
            find_phases(project_id="proj-123")  # All phases
            find_phases(project_id="proj-123", status="active")  # Active phase
            find_phases(project_id="proj-123", phase_id="phase-123")  # Get one
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
                # Single phase get mode
                if phase_id:
                    response = await client.get(
                        urljoin(api_url, f"/api/projects/{project_id}/phases/{phase_id}")
                    )

                    if response.status_code == 200:
                        result = response.json()
                        phase = result.get("phase", result)

                        # Get tasks for this phase if requested
                        if include_tasks:
                            tasks_response = await client.get(
                                urljoin(api_url, "/api/tasks"),
                                params={"phase_id": phase_id, "include_closed": True}
                            )
                            if tasks_response.status_code == 200:
                                tasks_result = tasks_response.json()
                                phase["tasks"] = tasks_result.get("tasks", [])
                                phase["task_count"] = len(phase["tasks"])

                        return json.dumps({"success": True, "phase": phase})
                    elif response.status_code == 404:
                        return MCPErrorFormatter.format_error(
                            error_type="not_found",
                            message=f"Phase {phase_id} not found",
                            suggestion="Verify the phase ID is correct",
                            http_status=404,
                        )
                    else:
                        return MCPErrorFormatter.from_http_error(response, "get phase")

                # List phases mode
                params: dict[str, Any] = {
                    "page": page,
                    "per_page": per_page,
                }

                if status:
                    valid_statuses = ["planning", "active", "complete"]
                    if status not in valid_statuses:
                        return MCPErrorFormatter.format_error(
                            error_type="validation_error",
                            message=f"Invalid status '{status}'",
                            suggestion=f"Use one of: {', '.join(valid_statuses)}",
                        )
                    params["status"] = status

                response = await client.get(
                    urljoin(api_url, f"/api/projects/{project_id}/phases"),
                    params=params,
                )

                if response.status_code != 200:
                    return MCPErrorFormatter.from_http_error(response, "list phases")

                result = response.json()
                phases = result.get("phases", result if isinstance(result, list) else [])

                # Add task counts if requested
                if include_tasks and phases:
                    for phase in phases:
                        tasks_response = await client.get(
                            urljoin(api_url, "/api/tasks"),
                            params={"phase_id": phase["id"], "per_page": 1}
                        )
                        if tasks_response.status_code == 200:
                            tasks_result = tasks_response.json()
                            phase["task_count"] = tasks_result.get("total_count", 0)

                return json.dumps({
                    "success": True,
                    "phases": phases,
                    "total_count": len(phases),
                    "project_id": project_id,
                })

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(
                e, "find phases", {"project_id": project_id}
            )
        except Exception as e:
            logger.error(f"Error finding phases: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, "find phases")

    @mcp.tool()
    async def manage_phase(
        ctx: Context,
        action: str,
        project_id: str,
        phase_id: str | None = None,
        title: str | None = None,
        description: str | None = None,
        phase_number: int | None = None,
        status: str | None = None,
        summary: str | None = None,
        goals: list[str] | None = None,
    ) -> str:
        """
        Manage phases (create/update/delete/activate/complete).

        Phases organize tasks into logical project stages. Each project can have
        multiple phases, but only one can be active at a time.

        Args:
            action: "create" | "update" | "delete" | "activate" | "complete"
            project_id: Project UUID (required)
            phase_id: Phase UUID (required for update/delete/activate/complete)
            title: Phase title (required for create)
            description: Phase description
            phase_number: Phase sequence number (auto-increments if not provided)
            status: Phase status ("planning", "active", "complete")
            summary: AI-generated summary (typically set when completing)
            goals: List of phase goals (strings)

        Returns:
            JSON with structure:
            - success: bool - Operation success status
            - phase: dict - The created/updated phase
            - message: str - Status message

        Phase Status Flow:
            planning -> active -> complete
            - "activate" action sets phase to active and completes any other active phase
            - "complete" action sets phase to complete with optional summary

        Examples:
            # Create a new phase
            manage_phase("create", project_id="p-1", title="Setup",
                        description="Initial project setup", goals=["Install deps", "Configure tools"])

            # Activate a phase (makes it current, completes previous active)
            manage_phase("activate", project_id="p-1", phase_id="ph-1")

            # Complete a phase with summary
            manage_phase("complete", project_id="p-1", phase_id="ph-1",
                        summary="Setup complete. All dependencies installed.")

            # Update phase details
            manage_phase("update", project_id="p-1", phase_id="ph-1", title="New Title")

            # Delete a phase
            manage_phase("delete", project_id="p-1", phase_id="ph-1")
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
                if action == "create":
                    if not title:
                        return MCPErrorFormatter.format_error(
                            error_type="validation_error",
                            message="title is required for create",
                            suggestion="Provide a phase title",
                        )

                    payload = {
                        "project_id": project_id,
                        "title": title,
                        "description": description or "",
                    }

                    if phase_number is not None:
                        payload["phase_number"] = phase_number
                    if goals:
                        payload["goals"] = goals

                    response = await client.post(
                        urljoin(api_url, f"/api/projects/{project_id}/phases"),
                        json=payload,
                    )

                    if response.status_code == 200:
                        result = response.json()
                        return json.dumps({
                            "success": True,
                            "phase": result.get("phase", result),
                            "message": result.get("message", "Phase created successfully"),
                        })
                    else:
                        return MCPErrorFormatter.from_http_error(response, "create phase")

                elif action == "update":
                    if not phase_id:
                        return MCPErrorFormatter.format_error(
                            error_type="validation_error",
                            message="phase_id is required for update",
                            suggestion="Provide the phase ID to update",
                        )

                    update_fields = {}
                    if title is not None:
                        update_fields["title"] = title
                    if description is not None:
                        update_fields["description"] = description
                    if phase_number is not None:
                        update_fields["phase_number"] = phase_number
                    if status is not None:
                        valid_statuses = ["planning", "active", "complete"]
                        if status not in valid_statuses:
                            return MCPErrorFormatter.format_error(
                                error_type="validation_error",
                                message=f"Invalid status '{status}'",
                                suggestion=f"Use one of: {', '.join(valid_statuses)}",
                            )
                        update_fields["status"] = status
                    if summary is not None:
                        update_fields["summary"] = summary
                    if goals is not None:
                        update_fields["goals"] = goals

                    if not update_fields:
                        return MCPErrorFormatter.format_error(
                            error_type="validation_error",
                            message="No fields to update",
                            suggestion="Provide at least one field to update",
                        )

                    response = await client.put(
                        urljoin(api_url, f"/api/projects/{project_id}/phases/{phase_id}"),
                        json=update_fields,
                    )

                    if response.status_code == 200:
                        result = response.json()
                        return json.dumps({
                            "success": True,
                            "phase": result.get("phase", result),
                            "message": result.get("message", "Phase updated successfully"),
                        })
                    else:
                        return MCPErrorFormatter.from_http_error(response, "update phase")

                elif action == "delete":
                    if not phase_id:
                        return MCPErrorFormatter.format_error(
                            error_type="validation_error",
                            message="phase_id is required for delete",
                            suggestion="Provide the phase ID to delete",
                        )

                    response = await client.delete(
                        urljoin(api_url, f"/api/projects/{project_id}/phases/{phase_id}")
                    )

                    if response.status_code == 200:
                        result = response.json()
                        return json.dumps({
                            "success": True,
                            "message": result.get("message", "Phase deleted successfully"),
                        })
                    else:
                        return MCPErrorFormatter.from_http_error(response, "delete phase")

                elif action == "activate":
                    if not phase_id:
                        return MCPErrorFormatter.format_error(
                            error_type="validation_error",
                            message="phase_id is required for activate",
                            suggestion="Provide the phase ID to activate",
                        )

                    response = await client.post(
                        urljoin(api_url, f"/api/projects/{project_id}/phases/{phase_id}/activate")
                    )

                    if response.status_code == 200:
                        result = response.json()
                        return json.dumps({
                            "success": True,
                            "phase": result.get("phase", result),
                            "completed_phases": result.get("completed_phases", []),
                            "message": result.get("message", "Phase activated"),
                        })
                    else:
                        return MCPErrorFormatter.from_http_error(response, "activate phase")

                elif action == "complete":
                    if not phase_id:
                        return MCPErrorFormatter.format_error(
                            error_type="validation_error",
                            message="phase_id is required for complete",
                            suggestion="Provide the phase ID to complete",
                        )

                    payload = {}
                    if summary:
                        payload["summary"] = summary

                    response = await client.post(
                        urljoin(api_url, f"/api/projects/{project_id}/phases/{phase_id}/complete"),
                        json=payload if payload else None,
                    )

                    if response.status_code == 200:
                        result = response.json()
                        return json.dumps({
                            "success": True,
                            "phase": result.get("phase", result),
                            "message": result.get("message", "Phase completed"),
                        })
                    else:
                        return MCPErrorFormatter.from_http_error(response, "complete phase")

                else:
                    return MCPErrorFormatter.format_error(
                        error_type="validation_error",
                        message=f"Unknown action: {action}",
                        suggestion="Use 'create', 'update', 'delete', 'activate', or 'complete'",
                    )

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(
                e, f"{action} phase", {"project_id": project_id, "phase_id": phase_id}
            )
        except Exception as e:
            logger.error(f"Error managing phase ({action}): {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, f"{action} phase")

    @mcp.tool()
    async def assign_task_phase(
        ctx: Context,
        task_id: str,
        phase_id: str | None = None,
    ) -> str:
        """
        Assign a task to a phase or remove phase assignment.

        Args:
            task_id: Task UUID (required)
            phase_id: Phase UUID to assign (or null/empty to remove assignment)

        Returns:
            JSON with structure:
            - success: bool - Operation success status
            - task: dict - The updated task
            - message: str - Status message

        Examples:
            # Assign task to phase
            assign_task_phase(task_id="task-123", phase_id="phase-456")

            # Remove task from phase
            assign_task_phase(task_id="task-123", phase_id=None)
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
                response = await client.put(
                    urljoin(api_url, f"/api/tasks/{task_id}"),
                    json={"phase_id": phase_id},
                )

                if response.status_code == 200:
                    result = response.json()
                    task = result.get("task", result)

                    if phase_id:
                        message = f"Task assigned to phase {phase_id}"
                    else:
                        message = "Task removed from phase"

                    return json.dumps({
                        "success": True,
                        "task": task,
                        "message": message,
                    })
                elif response.status_code == 404:
                    return MCPErrorFormatter.format_error(
                        error_type="not_found",
                        message=f"Task {task_id} not found",
                        suggestion="Verify the task ID is correct",
                        http_status=404,
                    )
                else:
                    return MCPErrorFormatter.from_http_error(response, "assign task phase")

        except httpx.RequestError as e:
            return MCPErrorFormatter.from_exception(
                e, "assign task phase", {"task_id": task_id, "phase_id": phase_id}
            )
        except Exception as e:
            logger.error(f"Error assigning task phase: {e}", exc_info=True)
            return MCPErrorFormatter.from_exception(e, "assign task phase")

    logger.info("Phase tools registered (find_phases, manage_phase, assign_task_phase)")

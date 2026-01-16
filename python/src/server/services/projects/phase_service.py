"""
Phase Service Module for Archon

This module provides core business logic for phase operations that can be
shared between MCP tools and FastAPI endpoints.
"""

from datetime import datetime
from typing import Any

from src.server.utils import get_supabase_client

from ...config.logfire_config import get_logger

logger = get_logger(__name__)


class PhaseService:
    """Service class for phase operations"""

    VALID_STATUSES = ["planning", "active", "complete"]

    def __init__(self, supabase_client=None):
        """Initialize with optional supabase client"""
        self.supabase_client = supabase_client or get_supabase_client()

    def validate_status(self, status: str) -> tuple[bool, str]:
        """Validate phase status"""
        if status not in self.VALID_STATUSES:
            return (
                False,
                f"Invalid status '{status}'. Must be one of: {', '.join(self.VALID_STATUSES)}",
            )
        return True, ""

    async def create_phase(
        self,
        project_id: str,
        title: str,
        phase_number: int | None = None,
        description: str = "",
        goals: list[str] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Create a new phase under a project.

        Args:
            project_id: UUID of the project
            title: Phase title
            phase_number: Optional phase number (auto-increments if not provided)
            description: Phase description
            goals: Optional list of phase goals

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            # Validate inputs
            if not title or not isinstance(title, str) or len(title.strip()) == 0:
                return False, {"error": "Phase title is required and must be a non-empty string"}

            if not project_id or not isinstance(project_id, str):
                return False, {"error": "Project ID is required and must be a string"}

            # Verify project exists
            project_check = (
                self.supabase_client.table("archon_projects")
                .select("id")
                .eq("id", project_id)
                .execute()
            )
            if not project_check.data:
                return False, {"error": f"Project with ID {project_id} not found"}

            # Auto-calculate phase_number if not provided
            if phase_number is None:
                max_phase_response = (
                    self.supabase_client.table("archon_phases")
                    .select("phase_number")
                    .eq("project_id", project_id)
                    .order("phase_number", desc=True)
                    .limit(1)
                    .execute()
                )
                if max_phase_response.data:
                    phase_number = max_phase_response.data[0]["phase_number"] + 1
                else:
                    phase_number = 1

            phase_data = {
                "project_id": project_id,
                "phase_number": phase_number,
                "title": title.strip(),
                "description": description,
                "status": "planning",
                "goals": goals or [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            response = self.supabase_client.table("archon_phases").insert(phase_data).execute()

            if response.data:
                phase = response.data[0]
                logger.info(f"Phase created: {phase['id']} - {title} (Phase {phase_number})")
                return True, {
                    "phase": {
                        "id": phase["id"],
                        "project_id": phase["project_id"],
                        "phase_number": phase["phase_number"],
                        "title": phase["title"],
                        "description": phase["description"],
                        "status": phase["status"],
                        "goals": phase.get("goals", []),
                        "created_at": phase["created_at"],
                    },
                    "message": f"Phase {phase_number}: {title} created successfully",
                }
            else:
                return False, {"error": "Failed to create phase"}

        except Exception as e:
            logger.error(f"Error creating phase: {e}")
            return False, {"error": f"Error creating phase: {str(e)}"}

    def list_phases(
        self,
        project_id: str,
        status: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        List phases for a project.

        Args:
            project_id: Filter by project (required)
            status: Filter by status (planning, active, complete)

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            if not project_id:
                return False, {"error": "project_id is required"}

            query = (
                self.supabase_client.table("archon_phases")
                .select("*")
                .eq("project_id", project_id)
            )

            if status:
                is_valid, error_msg = self.validate_status(status)
                if not is_valid:
                    return False, {"error": error_msg}
                query = query.eq("status", status)

            response = query.order("phase_number", desc=False).execute()

            phases = []
            for phase in response.data:
                phases.append({
                    "id": phase["id"],
                    "project_id": phase["project_id"],
                    "phase_number": phase["phase_number"],
                    "title": phase["title"],
                    "description": phase["description"],
                    "status": phase["status"],
                    "goals": phase.get("goals", []),
                    "summary": phase.get("summary"),
                    "created_at": phase["created_at"],
                    "started_at": phase.get("started_at"),
                    "completed_at": phase.get("completed_at"),
                })

            return True, {
                "phases": phases,
                "total_count": len(phases),
            }

        except Exception as e:
            logger.error(f"Error listing phases: {e}")
            return False, {"error": f"Error listing phases: {str(e)}"}

    def get_phase(self, phase_id: str) -> tuple[bool, dict[str, Any]]:
        """
        Get a specific phase by ID.

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            response = (
                self.supabase_client.table("archon_phases")
                .select("*")
                .eq("id", phase_id)
                .execute()
            )

            if response.data:
                phase = response.data[0]
                return True, {"phase": phase}
            else:
                return False, {"error": f"Phase with ID {phase_id} not found"}

        except Exception as e:
            logger.error(f"Error getting phase: {e}")
            return False, {"error": f"Error getting phase: {str(e)}"}

    def get_active_phase(self, project_id: str) -> tuple[bool, dict[str, Any]]:
        """
        Get the currently active phase for a project.

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            response = (
                self.supabase_client.table("archon_phases")
                .select("*")
                .eq("project_id", project_id)
                .eq("status", "active")
                .limit(1)
                .execute()
            )

            if response.data:
                phase = response.data[0]
                return True, {"phase": phase}
            else:
                return True, {"phase": None, "message": "No active phase for this project"}

        except Exception as e:
            logger.error(f"Error getting active phase: {e}")
            return False, {"error": f"Error getting active phase: {str(e)}"}

    async def update_phase(
        self, phase_id: str, update_fields: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        """
        Update phase with specified fields.

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            update_data = {"updated_at": datetime.now().isoformat()}

            # Validate and add fields
            if "title" in update_fields:
                update_data["title"] = update_fields["title"]

            if "description" in update_fields:
                update_data["description"] = update_fields["description"]

            if "status" in update_fields:
                is_valid, error_msg = self.validate_status(update_fields["status"])
                if not is_valid:
                    return False, {"error": error_msg}
                update_data["status"] = update_fields["status"]

                # Set timestamps based on status changes
                if update_fields["status"] == "active":
                    update_data["started_at"] = datetime.now().isoformat()
                elif update_fields["status"] == "complete":
                    update_data["completed_at"] = datetime.now().isoformat()

            if "summary" in update_fields:
                update_data["summary"] = update_fields["summary"]

            if "goals" in update_fields:
                update_data["goals"] = update_fields["goals"]

            if "phase_number" in update_fields:
                update_data["phase_number"] = update_fields["phase_number"]

            response = (
                self.supabase_client.table("archon_phases")
                .update(update_data)
                .eq("id", phase_id)
                .execute()
            )

            if response.data:
                phase = response.data[0]
                return True, {"phase": phase, "message": "Phase updated successfully"}
            else:
                return False, {"error": f"Phase with ID {phase_id} not found"}

        except Exception as e:
            logger.error(f"Error updating phase: {e}")
            return False, {"error": f"Error updating phase: {str(e)}"}

    async def delete_phase(self, phase_id: str) -> tuple[bool, dict[str, Any]]:
        """
        Delete a phase. Tasks with this phase_id will have it set to NULL.

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            # Check if phase exists
            check_response = (
                self.supabase_client.table("archon_phases")
                .select("id, title")
                .eq("id", phase_id)
                .execute()
            )
            if not check_response.data:
                return False, {"error": f"Phase with ID {phase_id} not found"}

            phase_title = check_response.data[0]["title"]

            # Get count of tasks that will be unlinked
            tasks_response = (
                self.supabase_client.table("archon_tasks")
                .select("id")
                .eq("phase_id", phase_id)
                .execute()
            )
            tasks_affected = len(tasks_response.data) if tasks_response.data else 0

            # Delete the phase (cascade will set task phase_id to NULL)
            self.supabase_client.table("archon_phases").delete().eq("id", phase_id).execute()

            return True, {
                "phase_id": phase_id,
                "title": phase_title,
                "tasks_unlinked": tasks_affected,
                "message": f"Phase '{phase_title}' deleted. {tasks_affected} tasks unlinked.",
            }

        except Exception as e:
            logger.error(f"Error deleting phase: {e}")
            return False, {"error": f"Error deleting phase: {str(e)}"}

    async def activate_phase(self, phase_id: str) -> tuple[bool, dict[str, Any]]:
        """
        Activate a phase, setting any other active phases to complete.

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            # Get the phase to activate
            phase_response = (
                self.supabase_client.table("archon_phases")
                .select("*")
                .eq("id", phase_id)
                .execute()
            )
            if not phase_response.data:
                return False, {"error": f"Phase with ID {phase_id} not found"}

            phase = phase_response.data[0]
            project_id = phase["project_id"]

            # Complete any currently active phases for this project
            active_phases = (
                self.supabase_client.table("archon_phases")
                .select("id")
                .eq("project_id", project_id)
                .eq("status", "active")
                .neq("id", phase_id)
                .execute()
            )

            completed_phases = []
            for active_phase in active_phases.data:
                self.supabase_client.table("archon_phases").update({
                    "status": "complete",
                    "completed_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }).eq("id", active_phase["id"]).execute()
                completed_phases.append(active_phase["id"])

            # Activate the target phase
            update_response = (
                self.supabase_client.table("archon_phases")
                .update({
                    "status": "active",
                    "started_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                })
                .eq("id", phase_id)
                .execute()
            )

            if update_response.data:
                return True, {
                    "phase": update_response.data[0],
                    "completed_phases": completed_phases,
                    "message": f"Phase '{phase['title']}' is now active",
                }
            else:
                return False, {"error": "Failed to activate phase"}

        except Exception as e:
            logger.error(f"Error activating phase: {e}")
            return False, {"error": f"Error activating phase: {str(e)}"}

    async def complete_phase(
        self, phase_id: str, summary: str | None = None
    ) -> tuple[bool, dict[str, Any]]:
        """
        Mark a phase as complete with optional summary.

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            update_data = {
                "status": "complete",
                "completed_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            if summary:
                update_data["summary"] = summary

            response = (
                self.supabase_client.table("archon_phases")
                .update(update_data)
                .eq("id", phase_id)
                .execute()
            )

            if response.data:
                phase = response.data[0]
                return True, {
                    "phase": phase,
                    "message": f"Phase '{phase['title']}' completed",
                }
            else:
                return False, {"error": f"Phase with ID {phase_id} not found"}

        except Exception as e:
            logger.error(f"Error completing phase: {e}")
            return False, {"error": f"Error completing phase: {str(e)}"}

    def get_phase_tasks(
        self,
        phase_id: str,
        include_closed: bool = False,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Get all tasks for a specific phase.

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            query = (
                self.supabase_client.table("archon_tasks")
                .select("*")
                .eq("phase_id", phase_id)
            )

            if not include_closed:
                query = query.neq("status", "done")

            response = query.order("task_order", desc=False).execute()

            tasks = response.data if response.data else []

            # Calculate stats
            status_counts = {"todo": 0, "doing": 0, "review": 0, "done": 0}
            for task in tasks:
                status = task.get("status", "todo")
                if status in status_counts:
                    status_counts[status] += 1

            return True, {
                "tasks": tasks,
                "total_count": len(tasks),
                "status_counts": status_counts,
            }

        except Exception as e:
            logger.error(f"Error getting phase tasks: {e}")
            return False, {"error": f"Error getting phase tasks: {str(e)}"}

    async def assign_task_to_phase(
        self,
        task_id: str,
        phase_id: str | None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Assign a task to a phase (or remove phase assignment if phase_id is None).

        Returns:
            Tuple of (success, result_dict)
        """
        try:
            # Verify task exists
            task_check = (
                self.supabase_client.table("archon_tasks")
                .select("id, title")
                .eq("id", task_id)
                .execute()
            )
            if not task_check.data:
                return False, {"error": f"Task with ID {task_id} not found"}

            # Verify phase exists (if provided)
            if phase_id:
                phase_check = (
                    self.supabase_client.table("archon_phases")
                    .select("id, title")
                    .eq("id", phase_id)
                    .execute()
                )
                if not phase_check.data:
                    return False, {"error": f"Phase with ID {phase_id} not found"}

            # Update task
            response = (
                self.supabase_client.table("archon_tasks")
                .update({
                    "phase_id": phase_id,
                    "updated_at": datetime.now().isoformat(),
                })
                .eq("id", task_id)
                .execute()
            )

            if response.data:
                task = response.data[0]
                if phase_id:
                    message = f"Task assigned to phase"
                else:
                    message = f"Task removed from phase"
                return True, {"task": task, "message": message}
            else:
                return False, {"error": "Failed to update task"}

        except Exception as e:
            logger.error(f"Error assigning task to phase: {e}")
            return False, {"error": f"Error assigning task to phase: {str(e)}"}

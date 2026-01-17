"""Unit tests for phase management tools."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.fastmcp import Context

from src.mcp_server.features.phases.phase_tools import register_phase_tools


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server for testing."""
    mock = MagicMock()
    mock._tools = {}

    def tool_decorator():
        def decorator(func):
            mock._tools[func.__name__] = func
            return func

        return decorator

    mock.tool = tool_decorator
    return mock


@pytest.fixture
def mock_context():
    """Create a mock context for testing."""
    return MagicMock(spec=Context)


# =============================================================================
# Tests for find_phases tool
# =============================================================================


class TestFindPhases:
    """Tests for the find_phases MCP tool."""

    @pytest.mark.asyncio
    async def test_find_phases_list_all(self, mock_mcp, mock_context):
        """Test listing all phases for a project."""
        register_phase_tools(mock_mcp)

        find_phases = mock_mcp._tools.get("find_phases")
        assert find_phases is not None, "find_phases tool not registered"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "phases": [
                {"id": "phase-1", "title": "Setup", "status": "complete"},
                {"id": "phase-2", "title": "Implementation", "status": "active"},
            ]
        }

        with patch("src.mcp_server.features.phases.phase_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await find_phases(mock_context, project_id="project-123")

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert len(result_data["phases"]) == 2
            assert result_data["total_count"] == 2
            assert result_data["project_id"] == "project-123"

    @pytest.mark.asyncio
    async def test_find_phases_by_id(self, mock_mcp, mock_context):
        """Test getting a specific phase by ID."""
        register_phase_tools(mock_mcp)

        find_phases = mock_mcp._tools.get("find_phases")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "phase": {
                "id": "phase-123",
                "title": "Implementation",
                "status": "active",
                "description": "Main implementation phase",
            }
        }

        with patch("src.mcp_server.features.phases.phase_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await find_phases(
                mock_context,
                project_id="project-123",
                phase_id="phase-123",
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["phase"]["id"] == "phase-123"
            assert result_data["phase"]["title"] == "Implementation"

    @pytest.mark.asyncio
    async def test_find_phases_filter_by_status(self, mock_mcp, mock_context):
        """Test filtering phases by status."""
        register_phase_tools(mock_mcp)

        find_phases = mock_mcp._tools.get("find_phases")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "phases": [{"id": "phase-2", "title": "Implementation", "status": "active"}]
        }

        with patch("src.mcp_server.features.phases.phase_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await find_phases(
                mock_context,
                project_id="project-123",
                status="active",
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert len(result_data["phases"]) == 1
            assert result_data["phases"][0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_find_phases_invalid_status(self, mock_mcp, mock_context):
        """Test that invalid status returns error."""
        register_phase_tools(mock_mcp)

        find_phases = mock_mcp._tools.get("find_phases")

        result = await find_phases(
            mock_context,
            project_id="project-123",
            status="invalid_status",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data
        assert result_data["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_find_phases_missing_project_id(self, mock_mcp, mock_context):
        """Test that missing project_id returns error."""
        register_phase_tools(mock_mcp)

        find_phases = mock_mcp._tools.get("find_phases")

        result = await find_phases(mock_context, project_id="")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data
        assert result_data["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_find_phases_not_found(self, mock_mcp, mock_context):
        """Test getting a non-existent phase."""
        register_phase_tools(mock_mcp)

        find_phases = mock_mcp._tools.get("find_phases")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Phase not found"

        with patch("src.mcp_server.features.phases.phase_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await find_phases(
                mock_context,
                project_id="project-123",
                phase_id="nonexistent",
            )

            result_data = json.loads(result)
            assert result_data["success"] is False
            assert result_data["error"]["type"] == "not_found"

    @pytest.mark.asyncio
    async def test_find_phases_with_task_counts(self, mock_mcp, mock_context):
        """Test listing phases with task counts."""
        register_phase_tools(mock_mcp)

        find_phases = mock_mcp._tools.get("find_phases")

        phases_response = MagicMock()
        phases_response.status_code = 200
        phases_response.json.return_value = {
            "phases": [
                {"id": "phase-1", "title": "Setup", "status": "complete"},
            ]
        }

        tasks_response = MagicMock()
        tasks_response.status_code = 200
        tasks_response.json.return_value = {"total_count": 5}

        with patch("src.mcp_server.features.phases.phase_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()

            call_count = 0

            async def get_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return phases_response
                return tasks_response

            mock_async_client.get.side_effect = get_side_effect
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await find_phases(
                mock_context,
                project_id="project-123",
                include_tasks=True,
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["phases"][0]["task_count"] == 5


# =============================================================================
# Tests for manage_phase tool
# =============================================================================


class TestManagePhase:
    """Tests for the manage_phase MCP tool."""

    @pytest.mark.asyncio
    async def test_create_phase(self, mock_mcp, mock_context):
        """Test creating a new phase."""
        register_phase_tools(mock_mcp)

        manage_phase = mock_mcp._tools.get("manage_phase")
        assert manage_phase is not None, "manage_phase tool not registered"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "phase": {
                "id": "phase-new",
                "title": "Testing Phase",
                "description": "Run all tests",
                "status": "planning",
            },
            "message": "Phase created successfully",
        }

        with patch("src.mcp_server.features.phases.phase_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await manage_phase(
                mock_context,
                action="create",
                project_id="project-123",
                title="Testing Phase",
                description="Run all tests",
                goals=["Unit tests", "Integration tests"],
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["phase"]["title"] == "Testing Phase"
            assert "Phase created" in result_data["message"]

    @pytest.mark.asyncio
    async def test_create_phase_missing_title(self, mock_mcp, mock_context):
        """Test creating phase without title fails."""
        register_phase_tools(mock_mcp)

        manage_phase = mock_mcp._tools.get("manage_phase")

        result = await manage_phase(
            mock_context,
            action="create",
            project_id="project-123",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert result_data["error"]["type"] == "validation_error"
        assert "title" in result_data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_update_phase(self, mock_mcp, mock_context):
        """Test updating a phase."""
        register_phase_tools(mock_mcp)

        manage_phase = mock_mcp._tools.get("manage_phase")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "phase": {
                "id": "phase-123",
                "title": "Updated Title",
                "status": "active",
            },
            "message": "Phase updated successfully",
        }

        with patch("src.mcp_server.features.phases.phase_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.put.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await manage_phase(
                mock_context,
                action="update",
                project_id="project-123",
                phase_id="phase-123",
                title="Updated Title",
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["phase"]["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_phase_missing_phase_id(self, mock_mcp, mock_context):
        """Test update without phase_id fails."""
        register_phase_tools(mock_mcp)

        manage_phase = mock_mcp._tools.get("manage_phase")

        result = await manage_phase(
            mock_context,
            action="update",
            project_id="project-123",
            title="New Title",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert result_data["error"]["type"] == "validation_error"
        assert "phase_id" in result_data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_update_phase_no_fields(self, mock_mcp, mock_context):
        """Test update with no fields fails."""
        register_phase_tools(mock_mcp)

        manage_phase = mock_mcp._tools.get("manage_phase")

        result = await manage_phase(
            mock_context,
            action="update",
            project_id="project-123",
            phase_id="phase-123",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert result_data["error"]["type"] == "validation_error"
        assert "No fields" in result_data["error"]["message"]

    @pytest.mark.asyncio
    async def test_update_phase_invalid_status(self, mock_mcp, mock_context):
        """Test update with invalid status fails."""
        register_phase_tools(mock_mcp)

        manage_phase = mock_mcp._tools.get("manage_phase")

        result = await manage_phase(
            mock_context,
            action="update",
            project_id="project-123",
            phase_id="phase-123",
            status="invalid_status",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert result_data["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_delete_phase(self, mock_mcp, mock_context):
        """Test deleting a phase."""
        register_phase_tools(mock_mcp)

        manage_phase = mock_mcp._tools.get("manage_phase")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Phase deleted successfully"}

        with patch("src.mcp_server.features.phases.phase_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.delete.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await manage_phase(
                mock_context,
                action="delete",
                project_id="project-123",
                phase_id="phase-123",
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert "deleted" in result_data["message"].lower()

    @pytest.mark.asyncio
    async def test_delete_phase_missing_phase_id(self, mock_mcp, mock_context):
        """Test delete without phase_id fails."""
        register_phase_tools(mock_mcp)

        manage_phase = mock_mcp._tools.get("manage_phase")

        result = await manage_phase(
            mock_context,
            action="delete",
            project_id="project-123",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert result_data["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_activate_phase(self, mock_mcp, mock_context):
        """Test activating a phase."""
        register_phase_tools(mock_mcp)

        manage_phase = mock_mcp._tools.get("manage_phase")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "phase": {"id": "phase-123", "status": "active"},
            "completed_phases": ["phase-old"],
            "message": "Phase activated",
        }

        with patch("src.mcp_server.features.phases.phase_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await manage_phase(
                mock_context,
                action="activate",
                project_id="project-123",
                phase_id="phase-123",
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["phase"]["status"] == "active"
            assert "completed_phases" in result_data

    @pytest.mark.asyncio
    async def test_activate_phase_missing_phase_id(self, mock_mcp, mock_context):
        """Test activate without phase_id fails."""
        register_phase_tools(mock_mcp)

        manage_phase = mock_mcp._tools.get("manage_phase")

        result = await manage_phase(
            mock_context,
            action="activate",
            project_id="project-123",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert result_data["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_complete_phase(self, mock_mcp, mock_context):
        """Test completing a phase."""
        register_phase_tools(mock_mcp)

        manage_phase = mock_mcp._tools.get("manage_phase")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "phase": {"id": "phase-123", "status": "complete", "summary": "All done!"},
            "message": "Phase completed",
        }

        with patch("src.mcp_server.features.phases.phase_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await manage_phase(
                mock_context,
                action="complete",
                project_id="project-123",
                phase_id="phase-123",
                summary="All done!",
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["phase"]["status"] == "complete"

    @pytest.mark.asyncio
    async def test_complete_phase_missing_phase_id(self, mock_mcp, mock_context):
        """Test complete without phase_id fails."""
        register_phase_tools(mock_mcp)

        manage_phase = mock_mcp._tools.get("manage_phase")

        result = await manage_phase(
            mock_context,
            action="complete",
            project_id="project-123",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert result_data["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_unknown_action(self, mock_mcp, mock_context):
        """Test unknown action returns error."""
        register_phase_tools(mock_mcp)

        manage_phase = mock_mcp._tools.get("manage_phase")

        result = await manage_phase(
            mock_context,
            action="unknown_action",
            project_id="project-123",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert result_data["error"]["type"] == "validation_error"
        assert "unknown_action" in result_data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_missing_project_id(self, mock_mcp, mock_context):
        """Test that missing project_id returns error."""
        register_phase_tools(mock_mcp)

        manage_phase = mock_mcp._tools.get("manage_phase")

        result = await manage_phase(
            mock_context,
            action="create",
            project_id="",
            title="Test Phase",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert result_data["error"]["type"] == "validation_error"


# =============================================================================
# Tests for assign_task_phase tool
# =============================================================================


class TestAssignTaskPhase:
    """Tests for the assign_task_phase MCP tool."""

    @pytest.mark.asyncio
    async def test_assign_task_to_phase(self, mock_mcp, mock_context):
        """Test assigning a task to a phase."""
        register_phase_tools(mock_mcp)

        assign_task_phase = mock_mcp._tools.get("assign_task_phase")
        assert assign_task_phase is not None, "assign_task_phase tool not registered"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "task": {"id": "task-123", "phase_id": "phase-456", "title": "Test Task"}
        }

        with patch("src.mcp_server.features.phases.phase_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.put.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await assign_task_phase(
                mock_context,
                task_id="task-123",
                phase_id="phase-456",
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["task"]["phase_id"] == "phase-456"
            assert "assigned to phase" in result_data["message"].lower()

    @pytest.mark.asyncio
    async def test_remove_task_from_phase(self, mock_mcp, mock_context):
        """Test removing a task from a phase."""
        register_phase_tools(mock_mcp)

        assign_task_phase = mock_mcp._tools.get("assign_task_phase")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "task": {"id": "task-123", "phase_id": None, "title": "Test Task"}
        }

        with patch("src.mcp_server.features.phases.phase_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.put.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await assign_task_phase(
                mock_context,
                task_id="task-123",
                phase_id=None,
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert "removed from phase" in result_data["message"].lower()

    @pytest.mark.asyncio
    async def test_assign_missing_task_id(self, mock_mcp, mock_context):
        """Test that missing task_id returns error."""
        register_phase_tools(mock_mcp)

        assign_task_phase = mock_mcp._tools.get("assign_task_phase")

        result = await assign_task_phase(
            mock_context,
            task_id="",
            phase_id="phase-456",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert result_data["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_assign_task_not_found(self, mock_mcp, mock_context):
        """Test assigning to non-existent task."""
        register_phase_tools(mock_mcp)

        assign_task_phase = mock_mcp._tools.get("assign_task_phase")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Task not found"

        with patch("src.mcp_server.features.phases.phase_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.put.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await assign_task_phase(
                mock_context,
                task_id="nonexistent",
                phase_id="phase-456",
            )

            result_data = json.loads(result)
            assert result_data["success"] is False
            assert result_data["error"]["type"] == "not_found"

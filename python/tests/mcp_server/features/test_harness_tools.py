"""Unit tests for harness automation tools."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.fastmcp import Context

from src.mcp_server.features.harness.harness_tools import (
    register_harness_tools,
    _parse_specification,
)


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server for testing."""
    mock = MagicMock()
    # Store registered tools
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
# Tests for _parse_specification helper function
# =============================================================================


class TestParseSpecification:
    """Tests for the specification parsing helper function."""

    def test_parse_numbered_list(self):
        """Test parsing a numbered list specification."""
        spec = "1. Create user model\n2. Add authentication\n3. Write tests"
        tasks = _parse_specification(spec)

        assert len(tasks) == 3
        assert tasks[0]["title"] == "Create user model"
        assert tasks[1]["title"] == "Add authentication"
        assert tasks[2]["title"] == "Write tests"

    def test_parse_bullet_list_dash(self):
        """Test parsing a bullet list with dashes."""
        spec = "- Setup database schema\n- Implement API endpoints\n- Add validation"
        tasks = _parse_specification(spec)

        assert len(tasks) == 3
        assert tasks[0]["title"] == "Setup database schema"
        assert tasks[1]["title"] == "Implement API endpoints"
        assert tasks[2]["title"] == "Add validation"

    def test_parse_bullet_list_asterisk(self):
        """Test parsing a bullet list with asterisks."""
        spec = "* First task\n* Second task\n* Third task"
        tasks = _parse_specification(spec)

        assert len(tasks) == 3
        assert tasks[0]["title"] == "First task"
        assert tasks[1]["title"] == "Second task"
        assert tasks[2]["title"] == "Third task"

    def test_parse_numbered_with_parenthesis(self):
        """Test parsing numbered list with parenthesis format."""
        spec = "1) Task one\n2) Task two\n3) Task three"
        tasks = _parse_specification(spec)

        assert len(tasks) == 3
        assert tasks[0]["title"] == "Task one"
        assert tasks[1]["title"] == "Task two"
        assert tasks[2]["title"] == "Task three"

    def test_parse_empty_specification(self):
        """Test parsing empty specification returns empty list."""
        spec = ""
        tasks = _parse_specification(spec)
        assert tasks == []

    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only specification returns empty list."""
        spec = "   \n\n   \n"
        tasks = _parse_specification(spec)
        assert tasks == []

    def test_parse_strips_trailing_periods(self):
        """Test that trailing periods are stripped from task titles."""
        spec = "1. Create the model.\n2. Write the tests."
        tasks = _parse_specification(spec)

        assert tasks[0]["title"] == "Create the model"
        assert tasks[1]["title"] == "Write the tests"

    def test_parse_handles_blank_lines(self):
        """Test that blank lines are skipped."""
        spec = "1. First task\n\n2. Second task\n\n\n3. Third task"
        tasks = _parse_specification(spec)

        assert len(tasks) == 3

    def test_parse_plain_text_multiple_sentences(self):
        """Test parsing plain text with multiple sentences in one line."""
        spec = "Build login page. Add form validation. Connect to auth API. Test everything thoroughly."
        tasks = _parse_specification(spec)

        # Should split on sentence boundaries for long text
        assert len(tasks) >= 3  # May vary based on length threshold


# =============================================================================
# Tests for harness_initialize tool
# =============================================================================


class TestHarnessInitialize:
    """Tests for the harness_initialize MCP tool."""

    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_mcp, mock_context):
        """Test successful project initialization with tasks."""
        register_harness_tools(mock_mcp)

        harness_initialize = mock_mcp._tools.get("harness_initialize")
        assert harness_initialize is not None, "harness_initialize tool not registered"

        # Mock project verification response
        project_response = MagicMock()
        project_response.status_code = 200
        project_response.json.return_value = {"id": "project-123", "title": "Test Project"}

        # Mock task creation responses
        task_response = MagicMock()
        task_response.status_code = 200
        task_response.json.return_value = {
            "task": {"id": "task-1", "title": "Task 1", "task_order": 100},
            "message": "Task created successfully",
        }

        with patch("src.mcp_server.features.harness.harness_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get.return_value = project_response
            mock_async_client.post.return_value = task_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await harness_initialize(
                mock_context,
                project_id="project-123",
                specification="1. First task\n2. Second task\n3. Third task",
                assignee="AI IDE Agent",
                feature="test-feature",
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["tasks_created"] == 3
            assert len(result_data["tasks"]) == 3
            assert result_data["project_id"] == "project-123"

    @pytest.mark.asyncio
    async def test_initialize_missing_project_id(self, mock_mcp, mock_context):
        """Test initialization fails with missing project_id."""
        register_harness_tools(mock_mcp)

        harness_initialize = mock_mcp._tools.get("harness_initialize")

        result = await harness_initialize(
            mock_context,
            project_id="",
            specification="1. Task",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data
        assert isinstance(result_data["error"], dict)
        assert result_data["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_initialize_empty_specification(self, mock_mcp, mock_context):
        """Test initialization fails with empty specification."""
        register_harness_tools(mock_mcp)

        harness_initialize = mock_mcp._tools.get("harness_initialize")

        result = await harness_initialize(
            mock_context,
            project_id="project-123",
            specification="",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data
        assert isinstance(result_data["error"], dict)
        assert result_data["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_initialize_project_not_found(self, mock_mcp, mock_context):
        """Test initialization fails when project not found."""
        register_harness_tools(mock_mcp)

        harness_initialize = mock_mcp._tools.get("harness_initialize")

        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Project not found"

        with patch("src.mcp_server.features.harness.harness_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await harness_initialize(
                mock_context,
                project_id="nonexistent",
                specification="1. Task",
            )

            result_data = json.loads(result)
            assert result_data["success"] is False
            assert "error" in result_data
            assert isinstance(result_data["error"], dict)
            assert result_data["error"]["type"] == "not_found"

    @pytest.mark.asyncio
    async def test_initialize_sets_task_order(self, mock_mcp, mock_context):
        """Test that tasks are created with incrementing task_order."""
        register_harness_tools(mock_mcp)

        harness_initialize = mock_mcp._tools.get("harness_initialize")

        project_response = MagicMock()
        project_response.status_code = 200
        project_response.json.return_value = {"id": "project-123"}

        task_orders = []

        def capture_task_order(*args, **kwargs):
            task_orders.append(kwargs["json"]["task_order"])
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"task": {"id": f"task-{len(task_orders)}", "task_order": kwargs["json"]["task_order"]}}
            return response

        with patch("src.mcp_server.features.harness.harness_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get.return_value = project_response
            mock_async_client.post.side_effect = capture_task_order
            mock_client.return_value.__aenter__.return_value = mock_async_client

            await harness_initialize(
                mock_context,
                project_id="project-123",
                specification="1. First\n2. Second\n3. Third",
            )

            # Tasks should have incrementing order: 100, 200, 300
            assert task_orders == [100, 200, 300]


# =============================================================================
# Tests for harness_next_task tool
# =============================================================================


class TestHarnessNextTask:
    """Tests for the harness_next_task MCP tool."""

    @pytest.mark.asyncio
    async def test_next_task_returns_todo(self, mock_mcp, mock_context):
        """Test getting next todo task when no doing task exists."""
        register_harness_tools(mock_mcp)

        harness_next_task = mock_mcp._tools.get("harness_next_task")
        assert harness_next_task is not None, "harness_next_task tool not registered"

        # Mock no doing tasks
        doing_response = MagicMock()
        doing_response.status_code = 200
        doing_response.json.return_value = {"tasks": []}

        # Mock todo tasks
        todo_response = MagicMock()
        todo_response.status_code = 200
        todo_response.json.return_value = {
            "tasks": [
                {"id": "task-2", "title": "Second Task", "task_order": 200, "status": "todo"},
                {"id": "task-1", "title": "First Task", "task_order": 100, "status": "todo"},
            ]
        }

        # Mock update response
        update_response = MagicMock()
        update_response.status_code = 200
        update_response.json.return_value = {
            "task": {"id": "task-1", "title": "First Task", "status": "doing"}
        }

        call_count = 0

        def get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return doing_response
            return todo_response

        with patch("src.mcp_server.features.harness.harness_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get.side_effect = get_side_effect
            mock_async_client.put.return_value = update_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await harness_next_task(
                mock_context,
                project_id="project-123",
                mark_as_doing=True,
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["resumed"] is False
            # Should return task with lowest task_order (task-1)
            assert result_data["task"]["id"] == "task-1"
            assert "Starting task" in result_data["message"]

    @pytest.mark.asyncio
    async def test_next_task_resumes_doing(self, mock_mcp, mock_context):
        """Test resuming an existing doing task."""
        register_harness_tools(mock_mcp)

        harness_next_task = mock_mcp._tools.get("harness_next_task")

        # Mock existing doing task
        doing_response = MagicMock()
        doing_response.status_code = 200
        doing_response.json.return_value = {
            "tasks": [{"id": "task-1", "title": "In Progress Task", "status": "doing"}]
        }

        # Mock todo count
        todo_response = MagicMock()
        todo_response.status_code = 200
        todo_response.json.return_value = {"total_count": 3}

        call_count = 0

        def get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return doing_response
            return todo_response

        with patch("src.mcp_server.features.harness.harness_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get.side_effect = get_side_effect
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await harness_next_task(
                mock_context,
                project_id="project-123",
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["resumed"] is True
            assert "Resuming" in result_data["message"]

    @pytest.mark.asyncio
    async def test_next_task_all_complete(self, mock_mcp, mock_context):
        """Test when all tasks are complete."""
        register_harness_tools(mock_mcp)

        harness_next_task = mock_mcp._tools.get("harness_next_task")

        # Mock no doing tasks
        doing_response = MagicMock()
        doing_response.status_code = 200
        doing_response.json.return_value = {"tasks": []}

        # Mock no todo tasks
        todo_response = MagicMock()
        todo_response.status_code = 200
        todo_response.json.return_value = {"tasks": []}

        # Mock no review tasks
        review_response = MagicMock()
        review_response.status_code = 200
        review_response.json.return_value = {"tasks": []}

        call_count = 0

        def get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return doing_response
            elif call_count == 2:
                return todo_response
            return review_response

        with patch("src.mcp_server.features.harness.harness_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get.side_effect = get_side_effect
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await harness_next_task(
                mock_context,
                project_id="project-123",
            )

            result_data = json.loads(result)
            assert result_data["success"] is False
            assert result_data["task"] is None
            assert "All tasks complete" in result_data["message"]

    @pytest.mark.asyncio
    async def test_next_task_missing_project_id(self, mock_mcp, mock_context):
        """Test next task fails with missing project_id."""
        register_harness_tools(mock_mcp)

        harness_next_task = mock_mcp._tools.get("harness_next_task")

        result = await harness_next_task(
            mock_context,
            project_id="",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data
        assert isinstance(result_data["error"], dict)
        assert result_data["error"]["type"] == "validation_error"


# =============================================================================
# Tests for harness_complete tool
# =============================================================================


class TestHarnessComplete:
    """Tests for the harness_complete MCP tool."""

    @pytest.mark.asyncio
    async def test_complete_success(self, mock_mcp, mock_context):
        """Test successfully completing a task."""
        register_harness_tools(mock_mcp)

        harness_complete = mock_mcp._tools.get("harness_complete")
        assert harness_complete is not None, "harness_complete tool not registered"

        # Mock successful update response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "task": {"id": "task-123", "title": "Test Task", "status": "done"}
        }

        with patch("src.mcp_server.features.harness.harness_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.put.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await harness_complete(
                mock_context,
                task_id="task-123",
                auto_commit=False,
            )

            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["task"]["status"] == "done"
            assert "Task completed" in result_data["message"]

    @pytest.mark.asyncio
    async def test_complete_missing_task_id(self, mock_mcp, mock_context):
        """Test complete fails with missing task_id."""
        register_harness_tools(mock_mcp)

        harness_complete = mock_mcp._tools.get("harness_complete")

        result = await harness_complete(
            mock_context,
            task_id="",
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data
        assert isinstance(result_data["error"], dict)
        assert result_data["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_complete_task_not_found(self, mock_mcp, mock_context):
        """Test complete fails when task not found."""
        register_harness_tools(mock_mcp)

        harness_complete = mock_mcp._tools.get("harness_complete")

        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Task not found"

        with patch("src.mcp_server.features.harness.harness_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.put.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            result = await harness_complete(
                mock_context,
                task_id="nonexistent",
            )

            result_data = json.loads(result)
            assert result_data["success"] is False
            assert "error" in result_data
            assert isinstance(result_data["error"], dict)
            assert result_data["error"]["type"] == "not_found"

    @pytest.mark.asyncio
    async def test_complete_with_auto_commit_not_git_repo(self, mock_mcp, mock_context):
        """Test auto_commit skips when not in git repository."""
        register_harness_tools(mock_mcp)

        harness_complete = mock_mcp._tools.get("harness_complete")

        # Mock successful task update
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "task": {"id": "task-123", "title": "Test Task", "status": "done"}
        }

        with patch("src.mcp_server.features.harness.harness_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.put.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            # Mock subprocess to simulate not being in a git repo
            with patch("subprocess.run") as mock_subprocess:
                mock_subprocess.return_value = MagicMock(returncode=128)  # git command fails

                result = await harness_complete(
                    mock_context,
                    task_id="task-123",
                    auto_commit=True,
                )

                result_data = json.loads(result)
                assert result_data["success"] is True
                assert result_data["commit"]["skipped"] is True
                assert "Not a git repository" in result_data["commit"]["reason"]

    @pytest.mark.asyncio
    async def test_complete_with_auto_commit_no_changes(self, mock_mcp, mock_context):
        """Test auto_commit skips when no changes to commit."""
        register_harness_tools(mock_mcp)

        harness_complete = mock_mcp._tools.get("harness_complete")

        # Mock successful task update
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "task": {"id": "task-123", "title": "Test Task", "status": "done"}
        }

        with patch("src.mcp_server.features.harness.harness_tools.httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.put.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_async_client

            call_count = 0

            def subprocess_side_effect(cmd, *args, **kwargs):
                nonlocal call_count
                call_count += 1

                result = MagicMock()
                if cmd[0:2] == ["git", "rev-parse"]:
                    result.returncode = 0
                    result.stdout = ".git"
                elif cmd[0:2] == ["git", "add"]:
                    result.returncode = 0
                elif cmd[0:2] == ["git", "status"]:
                    result.returncode = 0
                    result.stdout = ""  # No changes
                else:
                    result.returncode = 0

                return result

            with patch("subprocess.run", side_effect=subprocess_side_effect):
                result = await harness_complete(
                    mock_context,
                    task_id="task-123",
                    auto_commit=True,
                )

                result_data = json.loads(result)
                assert result_data["success"] is True
                assert result_data["commit"]["skipped"] is True
                assert "No changes" in result_data["commit"]["reason"]

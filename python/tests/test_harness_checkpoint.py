"""
Tests for harness checkpoint functionality.

These tests verify the checkpoint system for task progress persistence.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock


@pytest.fixture
def temp_repo_dir():
    """Create a temporary directory simulating a git repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a minimal git structure
        git_dir = Path(tmpdir) / ".git"
        git_dir.mkdir()
        yield Path(tmpdir)


@pytest.mark.asyncio
async def test_checkpoint_save_and_retrieve(temp_repo_dir):
    """Test saving and retrieving a checkpoint."""
    from src.mcp_server.features.harness.harness_tools import _manage_checkpoint

    # Mock git to return our temp directory
    async def mock_git_toplevel(*args, **kwargs):
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(
            str(temp_repo_dir).encode(), b""
        ))
        return mock_process

    with patch("asyncio.create_subprocess_exec", mock_git_toplevel):
        # Save a checkpoint
        task_id = "test-task-123"
        result = await _manage_checkpoint(
            task_id=task_id,
            step=3,
            files_modified=["src/foo.py", "tests/test_foo.py"],
            next_action="Add error handling",
            notes="In progress",
        )

        assert result["success"] is True
        assert result["checkpoint"]["task_id"] == task_id
        assert result["checkpoint"]["step"] == 3
        assert result["checkpoint"]["files_modified"] == ["src/foo.py", "tests/test_foo.py"]
        assert result["checkpoint"]["next_action"] == "Add error handling"
        assert result["checkpoint"]["notes"] == "In progress"
        assert "timestamp" in result["checkpoint"]

        # Verify file was created
        checkpoint_file = temp_repo_dir / ".harness" / "checkpoint.json"
        assert checkpoint_file.exists()

        # Retrieve the checkpoint
        retrieve_result = await _manage_checkpoint(task_id=task_id)
        assert retrieve_result["success"] is True
        assert retrieve_result["checkpoint"]["step"] == 3


@pytest.mark.asyncio
async def test_checkpoint_clear(temp_repo_dir):
    """Test clearing a checkpoint."""
    from src.mcp_server.features.harness.harness_tools import _manage_checkpoint

    async def mock_git_toplevel(*args, **kwargs):
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(
            str(temp_repo_dir).encode(), b""
        ))
        return mock_process

    with patch("asyncio.create_subprocess_exec", mock_git_toplevel):
        task_id = "test-task-456"

        # Save a checkpoint
        await _manage_checkpoint(
            task_id=task_id,
            step=1,
            next_action="Start implementation",
        )

        # Clear the checkpoint
        clear_result = await _manage_checkpoint(task_id=task_id, clear=True)
        assert clear_result["success"] is True
        assert clear_result["checkpoint"] is None

        # Verify checkpoint is gone
        retrieve_result = await _manage_checkpoint(task_id=task_id)
        assert retrieve_result["checkpoint"] is None


@pytest.mark.asyncio
async def test_checkpoint_update_partial(temp_repo_dir):
    """Test updating only some fields in a checkpoint."""
    from src.mcp_server.features.harness.harness_tools import _manage_checkpoint

    async def mock_git_toplevel(*args, **kwargs):
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(
            str(temp_repo_dir).encode(), b""
        ))
        return mock_process

    with patch("asyncio.create_subprocess_exec", mock_git_toplevel):
        task_id = "test-task-789"

        # Save initial checkpoint
        await _manage_checkpoint(
            task_id=task_id,
            step=1,
            files_modified=["src/a.py"],
            next_action="First action",
        )

        # Update only the step
        result = await _manage_checkpoint(
            task_id=task_id,
            step=2,
        )

        # Files should be preserved, step updated
        assert result["checkpoint"]["step"] == 2
        assert result["checkpoint"]["files_modified"] == ["src/a.py"]
        assert result["checkpoint"]["next_action"] == "First action"


@pytest.mark.asyncio
async def test_get_checkpoint_for_task(temp_repo_dir):
    """Test the helper function used by harness_next_task."""
    from src.mcp_server.features.harness.harness_tools import (
        _manage_checkpoint,
        _get_checkpoint_for_task,
    )

    async def mock_git_toplevel(*args, **kwargs):
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(
            str(temp_repo_dir).encode(), b""
        ))
        return mock_process

    with patch("asyncio.create_subprocess_exec", mock_git_toplevel):
        task_id = "test-task-helper"

        # No checkpoint initially
        result = await _get_checkpoint_for_task(task_id)
        assert result is None

        # Save a checkpoint
        await _manage_checkpoint(
            task_id=task_id,
            step=5,
            next_action="Continue work",
        )

        # Should return checkpoint now
        result = await _get_checkpoint_for_task(task_id)
        assert result is not None
        assert result["step"] == 5
        assert result["next_action"] == "Continue work"

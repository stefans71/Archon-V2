"""
Tests for PRP (Project Requirements Plan) storage functionality.

Tests the storage and retrieval of PRPs in the RAG knowledge base.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestPRPStorage:
    """Tests for prp_storage.py functions."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        mock = MagicMock()
        mock.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[{}])
        mock.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
        mock.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()
        mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        return mock

    def test_generate_prp_source_id(self):
        """Test that source_id is generated correctly."""
        from src.mcp_server.features.harness.prp_storage import _generate_prp_source_id

        project_id = "test-project-123"
        result = _generate_prp_source_id(project_id)
        assert result == "prp_test-project-123"

    def test_generate_prp_url(self):
        """Test that PRP URL is generated correctly."""
        from src.mcp_server.features.harness.prp_storage import _generate_prp_url

        project_id = "test-project-123"
        result = _generate_prp_url(project_id)
        assert result == "archon://projects/test-project-123/prp"

    @pytest.mark.asyncio
    async def test_store_prp_fallback_success(self, mock_supabase):
        """Test successful PRP storage via fallback method."""
        from src.mcp_server.features.harness.prp_storage import _store_prp_fallback

        mock_embedding = [0.1] * 1536  # Typical embedding dimension

        with patch("src.mcp_server.features.harness.prp_storage.get_supabase_client", return_value=mock_supabase):
            with patch("src.mcp_server.features.harness.prp_storage.create_embedding", new_callable=AsyncMock, return_value=mock_embedding):
                result = await _store_prp_fallback(
                    project_id="test-project-123",
                    project_title="Test Project",
                    specification="Build a REST API with authentication",
                )

        assert result["success"] is True
        assert result["source_id"] == "prp_test-project-123"
        assert result["url"] == "archon://projects/test-project-123/prp"
        assert result["method"] == "fallback"

        # Verify upsert was called for source
        mock_supabase.table.assert_any_call("archon_sources")

        # Verify delete was called to remove existing page
        mock_supabase.table.return_value.delete.return_value.eq.assert_called()

        # Verify insert was called for page
        mock_supabase.table.assert_any_call("archon_crawled_pages")

    @pytest.mark.asyncio
    async def test_retrieve_prp_found(self, mock_supabase):
        """Test successful PRP retrieval."""
        from src.mcp_server.features.harness.prp_storage import retrieve_prp_for_project

        # Set up mock to return a page
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "content": "Build a REST API with authentication",
                "metadata": {"project_id": "test-project-123"}
            }]
        )

        with patch("src.mcp_server.features.harness.prp_storage.get_supabase_client", return_value=mock_supabase):
            result = await retrieve_prp_for_project("test-project-123")

        assert result["success"] is True
        assert result["content"] == "Build a REST API with authentication"
        assert result["source_id"] == "prp_test-project-123"

    @pytest.mark.asyncio
    async def test_retrieve_prp_not_found(self, mock_supabase):
        """Test PRP retrieval when not found."""
        from src.mcp_server.features.harness.prp_storage import retrieve_prp_for_project

        # Set up mock to return no pages
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        with patch("src.mcp_server.features.harness.prp_storage.get_supabase_client", return_value=mock_supabase):
            result = await retrieve_prp_for_project("test-project-123")

        assert result["success"] is False
        assert "not found" in result["error"].lower() or "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_delete_prp_success(self, mock_supabase):
        """Test successful PRP deletion."""
        from src.mcp_server.features.harness.prp_storage import delete_prp_for_project

        with patch("src.mcp_server.features.harness.prp_storage.get_supabase_client", return_value=mock_supabase):
            result = await delete_prp_for_project("test-project-123")

        assert result["success"] is True
        assert result["source_id"] == "prp_test-project-123"

        # Verify both tables were cleaned up
        mock_supabase.table.assert_any_call("archon_crawled_pages")
        mock_supabase.table.assert_any_call("archon_sources")


class TestPRPIntegration:
    """Integration tests for PRP storage with harness tools."""

    @pytest.mark.asyncio
    async def test_get_prp_context_returns_none_when_not_found(self):
        """Test that _get_prp_context returns None when PRP doesn't exist."""
        from src.mcp_server.features.harness.harness_tools import _get_prp_context

        mock_result = {"success": False, "error": "Not found"}

        with patch("src.mcp_server.features.harness.prp_storage.retrieve_prp_for_project", new_callable=AsyncMock, return_value=mock_result):
            result = await _get_prp_context("nonexistent-project")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prp_context_returns_content_when_found(self):
        """Test that _get_prp_context returns content when PRP exists."""
        from src.mcp_server.features.harness.harness_tools import _get_prp_context

        mock_result = {
            "success": True,
            "content": "Build a REST API",
            "source_id": "prp_test-123",
            "url": "archon://projects/test-123/prp"
        }

        with patch("src.mcp_server.features.harness.prp_storage.retrieve_prp_for_project", new_callable=AsyncMock, return_value=mock_result):
            result = await _get_prp_context("test-123")

        assert result is not None
        assert result["content"] == "Build a REST API"
        assert result["source_id"] == "prp_test-123"
        assert result["url"] == "archon://projects/test-123/prp"

    @pytest.mark.asyncio
    async def test_get_prp_context_handles_exceptions(self):
        """Test that _get_prp_context handles exceptions gracefully."""
        from src.mcp_server.features.harness.harness_tools import _get_prp_context

        with patch("src.mcp_server.features.harness.prp_storage.retrieve_prp_for_project", new_callable=AsyncMock, side_effect=Exception("Database error")):
            result = await _get_prp_context("test-123")

        assert result is None

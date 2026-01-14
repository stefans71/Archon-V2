"""Tests for git configuration module."""

import os
from unittest.mock import patch

import pytest

from src.mcp_server.utils.git_config import (
    GitConfig,
    GitExecutionMode,
    get_git_config,
    reset_git_config,
)


class TestGitConfig:
    """Tests for GitConfig class."""

    def setup_method(self):
        """Reset config cache before each test."""
        reset_git_config()

    def teardown_method(self):
        """Reset config cache after each test."""
        reset_git_config()

    def test_default_config_is_local(self):
        """Default config should use local execution mode."""
        with patch.dict(os.environ, {}, clear=True):
            config = GitConfig.from_env()

        assert config.mode == GitExecutionMode.LOCAL
        assert config.timeout_seconds == 60
        assert config.remote_host is None
        assert config.remote_user is None
        assert config.remote_path is None

    def test_local_mode_explicit(self):
        """Explicit local mode should work."""
        env = {"GIT_EXECUTION_MODE": "local"}
        with patch.dict(os.environ, env, clear=True):
            config = GitConfig.from_env()

        assert config.mode == GitExecutionMode.LOCAL
        assert not config.is_remote

    def test_remote_mode_with_all_required_vars(self):
        """Remote mode should work when all required vars are set."""
        env = {
            "GIT_EXECUTION_MODE": "remote",
            "GIT_REMOTE_HOST": "test-host",
            "GIT_REMOTE_USER": "test-user",
            "GIT_REMOTE_PATH": "/path/to/repo",
        }
        with patch.dict(os.environ, env, clear=True):
            config = GitConfig.from_env()

        assert config.mode == GitExecutionMode.REMOTE
        assert config.is_remote
        assert config.remote_host == "test-host"
        assert config.remote_user == "test-user"
        assert config.remote_path == "/path/to/repo"
        assert config.ssh_target == "test-user@test-host"

    def test_remote_mode_missing_host_raises(self):
        """Remote mode without host should raise ValueError."""
        env = {
            "GIT_EXECUTION_MODE": "remote",
            "GIT_REMOTE_USER": "test-user",
            "GIT_REMOTE_PATH": "/path/to/repo",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError) as exc_info:
                GitConfig.from_env()

        assert "GIT_REMOTE_HOST" in str(exc_info.value)

    def test_remote_mode_missing_user_raises(self):
        """Remote mode without user should raise ValueError."""
        env = {
            "GIT_EXECUTION_MODE": "remote",
            "GIT_REMOTE_HOST": "test-host",
            "GIT_REMOTE_PATH": "/path/to/repo",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError) as exc_info:
                GitConfig.from_env()

        assert "GIT_REMOTE_USER" in str(exc_info.value)

    def test_remote_mode_missing_path_raises(self):
        """Remote mode without path should raise ValueError."""
        env = {
            "GIT_EXECUTION_MODE": "remote",
            "GIT_REMOTE_HOST": "test-host",
            "GIT_REMOTE_USER": "test-user",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError) as exc_info:
                GitConfig.from_env()

        assert "GIT_REMOTE_PATH" in str(exc_info.value)

    def test_remote_mode_missing_multiple_vars_raises(self):
        """Remote mode with multiple missing vars should list all."""
        env = {"GIT_EXECUTION_MODE": "remote"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError) as exc_info:
                GitConfig.from_env()

        error_msg = str(exc_info.value)
        assert "GIT_REMOTE_HOST" in error_msg
        assert "GIT_REMOTE_USER" in error_msg
        assert "GIT_REMOTE_PATH" in error_msg

    def test_invalid_mode_raises(self):
        """Invalid execution mode should raise ValueError."""
        env = {"GIT_EXECUTION_MODE": "invalid"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError) as exc_info:
                GitConfig.from_env()

        assert "Invalid GIT_EXECUTION_MODE" in str(exc_info.value)

    def test_custom_timeout(self):
        """Custom timeout should be parsed correctly."""
        env = {"GIT_OPERATION_TIMEOUT": "120"}
        with patch.dict(os.environ, env, clear=True):
            config = GitConfig.from_env()

        assert config.timeout_seconds == 120

    def test_invalid_timeout_raises(self):
        """Invalid timeout should raise ValueError."""
        env = {"GIT_OPERATION_TIMEOUT": "not-a-number"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError) as exc_info:
                GitConfig.from_env()

        assert "Invalid GIT_OPERATION_TIMEOUT" in str(exc_info.value)

    def test_ssh_target_none_for_local(self):
        """Local mode should have None ssh_target."""
        with patch.dict(os.environ, {}, clear=True):
            config = GitConfig.from_env()

        assert config.ssh_target is None


class TestGetGitConfig:
    """Tests for get_git_config function."""

    def setup_method(self):
        """Reset config cache before each test."""
        reset_git_config()

    def teardown_method(self):
        """Reset config cache after each test."""
        reset_git_config()

    def test_caches_config(self):
        """get_git_config should cache the configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config1 = get_git_config()
            config2 = get_git_config()

        assert config1 is config2

    def test_reset_clears_cache(self):
        """reset_git_config should clear the cache."""
        with patch.dict(os.environ, {}, clear=True):
            config1 = get_git_config()
            reset_git_config()
            config2 = get_git_config()

        # Should be different objects
        assert config1 is not config2

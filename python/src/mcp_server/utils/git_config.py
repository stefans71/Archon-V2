"""
Git configuration for harness tools.

Supports two execution modes:
- local: Run git commands directly (default)
- remote: Run git commands via SSH on a remote server

This is useful when working over SSHFS where local git operations
can be slow or unreliable.
"""

import os
from dataclasses import dataclass
from enum import Enum


class GitExecutionMode(Enum):
    """Git command execution mode."""
    LOCAL = "local"
    REMOTE = "remote"


@dataclass
class GitConfig:
    """Configuration for git operations."""
    mode: GitExecutionMode
    timeout_seconds: int
    remote_host: str | None
    remote_user: str | None
    remote_path: str | None
    local_repo_path: str | None  # For local mode: path to repo in container

    @classmethod
    def from_env(cls) -> "GitConfig":
        """
        Load git configuration from environment variables.

        Environment variables:
            GIT_EXECUTION_MODE: "local" or "remote" (default: "local")
            GIT_OPERATION_TIMEOUT: Timeout in seconds (default: 60)
            GIT_REMOTE_HOST: SSH host for remote mode (required if remote)
            GIT_REMOTE_USER: SSH user for remote mode (required if remote)
            GIT_REMOTE_PATH: Repository path on remote (required if remote)

        Returns:
            GitConfig instance

        Raises:
            ValueError: If remote mode is configured but required vars are missing
        """
        mode_str = os.getenv("GIT_EXECUTION_MODE", "local").lower()

        try:
            mode = GitExecutionMode(mode_str)
        except ValueError:
            raise ValueError(
                f"Invalid GIT_EXECUTION_MODE: '{mode_str}'. "
                f"Valid values: 'local', 'remote'"
            )

        timeout_str = os.getenv("GIT_OPERATION_TIMEOUT", "60")
        try:
            timeout = int(timeout_str)
        except ValueError:
            raise ValueError(
                f"Invalid GIT_OPERATION_TIMEOUT: '{timeout_str}'. "
                f"Must be an integer (seconds)."
            )

        remote_host = os.getenv("GIT_REMOTE_HOST")
        remote_user = os.getenv("GIT_REMOTE_USER")
        remote_path = os.getenv("GIT_REMOTE_PATH")
        local_repo_path = os.getenv("GIT_REPO_PATH")

        if mode == GitExecutionMode.REMOTE:
            missing = []
            if not remote_host:
                missing.append("GIT_REMOTE_HOST")
            if not remote_user:
                missing.append("GIT_REMOTE_USER")
            if not remote_path:
                missing.append("GIT_REMOTE_PATH")

            if missing:
                raise ValueError(
                    f"Remote git execution requires: {', '.join(missing)}. "
                    f"Set these environment variables or use GIT_EXECUTION_MODE=local"
                )

        return cls(
            mode=mode,
            timeout_seconds=timeout,
            remote_host=remote_host,
            remote_user=remote_user,
            remote_path=remote_path,
            local_repo_path=local_repo_path,
        )

    @property
    def is_remote(self) -> bool:
        """Check if using remote execution mode."""
        return self.mode == GitExecutionMode.REMOTE

    @property
    def ssh_target(self) -> str | None:
        """Get SSH target string (user@host) for remote mode."""
        if self.is_remote and self.remote_user and self.remote_host:
            return f"{self.remote_user}@{self.remote_host}"
        return None


# Cached config instance
_config: GitConfig | None = None


def get_git_config() -> GitConfig:
    """
    Get or create the git configuration instance.

    Configuration is cached after first load.
    """
    global _config
    if _config is None:
        _config = GitConfig.from_env()
    return _config


def reset_git_config() -> None:
    """Reset cached config (useful for testing)."""
    global _config
    _config = None

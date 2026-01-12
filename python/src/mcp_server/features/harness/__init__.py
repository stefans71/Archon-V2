"""
Harness tools for Archon MCP Server.

This module provides tools for task automation workflows:
- harness_initialize: Parse specs and create tasks automatically
- harness_next_task: Get next todo task with smart selection
- harness_complete: Mark task done and optionally commit to git
"""

from .harness_tools import register_harness_tools

__all__ = ["register_harness_tools"]

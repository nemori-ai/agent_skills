"""MCP Server for agent skills.

This module provides the main entry point for the MCP server.
Designed to run in a Docker container with pre-configured environment.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from agent_skills.mcp.tools import register_tools


def get_default_skills_dir() -> Path:
    """Get the default built-in skills directory.
    
    Returns:
        Path to the built-in skills directory (agent_skills/skills/)
    """
    return Path(__file__).parent.parent / "skills"


def create_server(
    skills_dirs: list[str] | None = None,
) -> FastMCP:
    """
    Create and configure an MCP server with agent-skills tools.

    The server provides 8 tools:
    - skills_run: Run skill scripts
    - skills_ls: List files/directories
    - skills_read: Read file content
    - skills_write: Write/modify files
    - skills_create: Create new skills
    - skills_upload: Upload files (Base64)
    - skills_download: Download files (Base64)
    - skills_bash: Execute shell commands

    Args:
        skills_dirs: Additional directories to search for skills

    Returns:
        Configured FastMCP server instance
    """
    # Create server
    mcp = FastMCP(
        name="agent-skills",
    )

    # Register all tools
    register_tools(mcp, skills_dirs)

    return mcp


def main() -> None:
    """Main entry point for the MCP server CLI."""
    parser = argparse.ArgumentParser(
        description="Agent Skills MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server (default mode)
  agent-skills-server

  # Start with additional skills directory
  agent-skills-server --skills-dir /path/to/skills

  # Start with SSE transport
  agent-skills-server --transport sse

Environment Variables:
  SKILLS_WORKSPACE: Workspace directory (default: /workspace)
  SKILLS_DIR: Skills directory (default: /skills)

Docker Usage:
  docker run -i --rm \\
    -v ~/.agent-skills/skills:/skills:ro \\
    agent-skills:latest
        """,
    )

    parser.add_argument(
        "--skills-dir", "-s",
        type=str,
        action="append",
        default=[],
        help="Additional skills directory (can be specified multiple times)",
    )

    parser.add_argument(
        "--transport", "-t",
        type=str,
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress all logging output",
    )

    args = parser.parse_args()

    # Suppress logging if --quiet is set
    if args.quiet:
        logging.disable(logging.CRITICAL)
        logging.getLogger().handlers = []
        logging.getLogger("mcp").setLevel(logging.CRITICAL)
        logging.getLogger("uvicorn").setLevel(logging.CRITICAL)

    # Create server
    mcp = create_server(
        skills_dirs=args.skills_dir if args.skills_dir else None,
    )

    # Run server
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        mcp.run(transport="sse")


if __name__ == "__main__":
    main()

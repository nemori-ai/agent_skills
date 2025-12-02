"""MCP Server for agent skills.

This module provides the main entry point for the MCP server.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from agent_skills.mcp.tools import register_tools
from agent_skills.sandbox.sandbox import SandboxConfig


def get_default_skills_dir() -> Path:
    """Get the default built-in skills directory.
    
    Returns:
        Path to the built-in skills directory (agent_skills/skills/)
    """
    return Path(__file__).parent.parent / "skills"


def create_server(
    workspace_root: str | None = None,
    skills_dirs: list[str] | None = None,
    allow_write: bool = True,
    allow_network: bool = False,
    sandbox_to_skills: bool = True,
) -> FastMCP:
    """
    Create and configure an MCP server with agent-skills tools.

    Args:
        workspace_root: Root directory for file operations.
                       If sandbox_to_skills=True (default), this is ignored and
                       the built-in skills directory is used.
        skills_dirs: Additional directories to search for skills
        allow_write: Whether to allow write operations
        allow_network: Whether to allow network access in commands
        sandbox_to_skills: If True (default), sandbox the agent to the skills
                          directory only. Agent cannot access anything outside.
                          If False, use workspace_root as the sandbox root.

    Returns:
        Configured FastMCP server instance
    """
    # Create server
    mcp = FastMCP(
        name="agent-skills",
    )

    # Determine the sandbox root
    if sandbox_to_skills:
        # Sandbox to the built-in skills directory
        # Agent can only see and operate on skills
        sandbox_root = str(get_default_skills_dir())
    else:
        # Use provided workspace_root or cwd
        sandbox_root = workspace_root or os.getcwd()

    # Configure sandbox
    sandbox_config = SandboxConfig(
        workspace_root=sandbox_root,
        allow_write=allow_write,
        allow_network=allow_network,
    )

    # Register all tools
    # Note: skills_dirs is still used to discover additional skills,
    # but the sandbox root determines where commands execute
    register_tools(mcp, sandbox_config, skills_dirs)

    return mcp


def main() -> None:
    """Main entry point for the MCP server CLI."""
    parser = argparse.ArgumentParser(
        description="Agent Skills MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server (agent is sandboxed to skills directory by default)
  agent-skills-server

  # Start with custom workspace (disables skills sandbox)
  agent-skills-server --workspace /path/to/project --no-skills-sandbox

  # Start with additional skills directory
  agent-skills-server --skills-dir /path/to/skills

  # Read-only mode
  agent-skills-server --read-only
        """,
    )

    parser.add_argument(
        "--workspace", "-w",
        type=str,
        default=None,
        help="Workspace root directory (only used with --no-skills-sandbox)",
    )

    parser.add_argument(
        "--skills-dir", "-s",
        type=str,
        action="append",
        default=[],
        help="Additional skills directory (can be specified multiple times)",
    )

    parser.add_argument(
        "--no-skills-sandbox",
        action="store_true",
        help="Disable skills sandbox (allow agent to access workspace_root instead)",
    )

    parser.add_argument(
        "--read-only", "-r",
        action="store_true",
        help="Disable write operations",
    )

    parser.add_argument(
        "--allow-network", "-n",
        action="store_true",
        help="Allow network access in bash commands",
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
        # Also suppress rich console handler used by fastmcp
        logging.getLogger().handlers = []
        logging.getLogger("mcp").setLevel(logging.CRITICAL)
        logging.getLogger("uvicorn").setLevel(logging.CRITICAL)

    # Create server
    mcp = create_server(
        workspace_root=args.workspace,
        skills_dirs=args.skills_dir if args.skills_dir else None,
        allow_write=not args.read_only,
        allow_network=args.allow_network,
        sandbox_to_skills=not args.no_skills_sandbox,
    )

    # Run server
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        mcp.run(transport="sse")


if __name__ == "__main__":
    main()


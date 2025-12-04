"""MCP Tool definitions for agent skills.

Provides 6 tools with skills_ prefix for a Docker-based execution environment.
Skills are exposed as MCP Resources for progressive disclosure.

Supports flexible path resolution:
- skills/xxx         -> SKILLS_DIR/xxx (skill directories, read-write)
- workspace/xxx      -> WORKSPACE_DIR/xxx (user's workspace, read-write)
- ./xxx or xxx       -> WORKSPACE_DIR/xxx (relative to workspace)
- /absolute/path     -> direct access (backwards compatible)
"""

# pyright: reportUnusedFunction=false

from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from agent_skills.core.skill_manager import SKILL_FILE_NAME, SkillManager
from agent_skills.core.types import ToolStatus
from agent_skills.mcp.prompts import SKILL_GUIDE_PROMPT


# ============================================
# Path Configuration
# ============================================
# Skills directory for skill packages (read-only)
SKILLS_DIR = Path(os.environ.get("SKILLS_DIR", "/skills"))
# Workspace directory - user mounts their project here (read-write)
WORKSPACE_DIR = Path(os.environ.get("SKILLS_WORKSPACE", "/workspace"))


def resolve_path(path: str, allow_absolute: bool = True) -> Path:
    """Resolve a virtual path to an actual filesystem path.
    
    Path Resolution Rules:
    1. "skills/xxx"     -> SKILLS_DIR/xxx (skill packages)
    2. "workspace/xxx"  -> WORKSPACE_DIR/xxx (user's mounted workspace)
    3. "./xxx" or "xxx" -> WORKSPACE_DIR/xxx (relative paths)
    4. "/absolute/path" -> direct use if allow_absolute=True
    
    Args:
        path: The path to resolve
        allow_absolute: Whether to allow absolute paths (for backwards compatibility)
        
    Returns:
        Resolved Path object
    """
    path = path.strip()
    
    # Handle empty path
    if not path or path == "/":
        return WORKSPACE_DIR
    
    # Virtual path prefixes
    if path.startswith("skills/"):
        # Remove "skills/" prefix and resolve against SKILLS_DIR
        return SKILLS_DIR / path[7:]  # len("skills/") = 7
    
    if path.startswith("workspace/"):
        return WORKSPACE_DIR / path[10:]  # len("workspace/") = 10
    
    # Relative path (./xxx or just xxx without prefix)
    if path.startswith("./"):
        return WORKSPACE_DIR / path[2:]
    
    # Absolute path - check if allowed and if it exists
    if path.startswith("/"):
        if allow_absolute:
            return Path(path)
        else:
            # Fall back to workspace for security
            return WORKSPACE_DIR / path.lstrip("/")
    
    # Default: treat as relative to workspace
    return WORKSPACE_DIR / path


def get_path_info() -> dict[str, str]:
    """Get information about configured paths for debugging."""
    return {
        "skills": str(SKILLS_DIR),
        "workspace": str(WORKSPACE_DIR),
        "workspace_exists": str(WORKSPACE_DIR.exists()),
    }


async def _run_with_uv_isolation(
    scripts_dir: Path,
    command: str,
    timeout: int = 120,
) -> tuple[str, int]:
    """Run a command in an isolated uv virtual environment.

    Creates a temporary virtual environment using uv, installs dependencies
    from pyproject.toml, executes the command, and cleans up the environment.

    Args:
        scripts_dir: Path to the scripts directory containing pyproject.toml
        command: Command to execute (e.g., "python main.py arg1 arg2")
        timeout: Maximum execution time in seconds

    Returns:
        Tuple of (output string, exit code)
    """
    venv_path = scripts_dir / ".venv"
    output_parts: list[str] = []

    # Create a clean environment without VIRTUAL_ENV to avoid uv warnings
    clean_env = os.environ.copy()
    clean_env.pop("VIRTUAL_ENV", None)
    clean_env.pop("CONDA_PREFIX", None)
    clean_env.pop("CONDA_DEFAULT_ENV", None)

    try:
        # Step 1: Create venv and install dependencies using uv sync
        sync_process = await asyncio.create_subprocess_exec(
            "uv", "sync", "--quiet",
            cwd=str(scripts_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=clean_env,
        )
        _, sync_stderr = await asyncio.wait_for(
            sync_process.communicate(),
            timeout=timeout,
        )

        if sync_process.returncode != 0:
            error_msg = sync_stderr.decode("utf-8", errors="replace")
            return f"Failed to setup environment:\n{error_msg}", sync_process.returncode or 1

        # Step 2: Execute the command using uv run
        run_process = await asyncio.create_subprocess_shell(
            f"uv run {command}",
            cwd=str(scripts_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=clean_env,
        )
        run_stdout, run_stderr = await asyncio.wait_for(
            run_process.communicate(),
            timeout=timeout,
        )

        stdout_text = run_stdout.decode("utf-8", errors="replace")
        stderr_text = run_stderr.decode("utf-8", errors="replace")

        if stdout_text:
            output_parts.append(stdout_text)
        if stderr_text:
            output_parts.append(stderr_text)

        return "\n".join(output_parts) if output_parts else "", run_process.returncode or 0

    except asyncio.TimeoutError:
        return f"Command timed out after {timeout} seconds", 124

    except Exception as e:
        return f"Execution error: {e}", 1

    finally:
        # Cleanup: remove virtual environment and lockfile
        if venv_path.exists():
            try:
                shutil.rmtree(venv_path)
            except Exception:
                pass
        
        lockfile_path = scripts_dir / "uv.lock"
        if lockfile_path.exists():
            try:
                lockfile_path.unlink()
            except Exception:
                pass


def register_tools(
    mcp: FastMCP,
    skills_dirs: list[str] | None = None,
) -> dict[str, Any]:
    """
    Register all agent-skills tools and resources with an MCP server.

    This registers:
    - 6 tools: skills_run, skills_ls, skills_read, skills_write, 
               skills_create, skills_bash
    - N resources: skill://{name} for each discovered skill

    Args:
        mcp: FastMCP server instance
        skills_dirs: Optional list of skill directories

    Returns:
        Dictionary of initialized components for reference
    """
    # Ensure workspace directory exists
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize skill manager with a simple config
    skill_manager = _create_skill_manager(skills_dirs)

    # ============================================
    # Skill Resources (Progressive Disclosure)
    # ============================================

    @mcp.prompt()
    def skill_guide() -> str:
        """Get a comprehensive guide on how to use and create skills."""
        return SKILL_GUIDE_PROMPT

    # Register each discovered skill as a concrete resource
    def _make_skill_reader(skill_path: str):
        """Factory function to create a skill reader with captured path."""
        def reader() -> str:
            skill_file = Path(skill_path) / SKILL_FILE_NAME
            return skill_file.read_text(encoding="utf-8")
        return reader

    for skill_info in skill_manager.discover_skills():
        mcp.resource(
            f"skill://{skill_info.name}",
            name=skill_info.name,
            description=skill_info.description,
            mime_type="text/markdown",
        )(_make_skill_reader(skill_info.path))

    # ============================================
    # Tool 1: skills_run - Run skill scripts
    # ============================================

    @mcp.tool()
    async def skills_run(
        name: str = Field(description="Skill name"),
        command: str = Field(description="Command to execute in skill directory"),
        timeout: int = Field(default=120, description="Maximum execution time in seconds"),
    ) -> str:
        """Run a command inside a skill directory.

        Executes the command with the skill's directory as the working directory.
        If the skill has a `scripts/pyproject.toml`, the command runs in an
        isolated virtual environment managed by uv.

        Examples:
        - skills_run(name="gcd-calculator", command="python scripts/gcd.py 12 18")
        - skills_run(name="my-tool", command="bash scripts/setup.sh")
        """
        skill_path = skill_manager.get_skill_path(name)
        if not skill_path:
            return f"Error: skill '{name}' not found"

        actual_timeout = timeout if isinstance(timeout, int) else 120

        # Check if scripts/pyproject.toml exists for uv isolation
        scripts_dir = skill_path / "scripts"
        pyproject_path = scripts_dir / "pyproject.toml"

        if pyproject_path.exists():
            # Use uv isolation
            adjusted_command = command
            if "scripts/" in command:
                adjusted_command = command.replace("scripts/", "")
            
            output, exit_code = await _run_with_uv_isolation(
                scripts_dir=scripts_dir,
                command=adjusted_command,
                timeout=actual_timeout,
            )
            if exit_code != 0:
                return f"Exit code: {exit_code}\n{output}"
            return output

        # No pyproject.toml - use direct execution
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(skill_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=actual_timeout,
            )
            
            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                output += "\n" + stderr.decode("utf-8", errors="replace")
            
            if process.returncode != 0:
                return f"Exit code: {process.returncode}\n{output}"
            return output
            
        except asyncio.TimeoutError:
            return f"Command timed out after {actual_timeout} seconds"
        except Exception as e:
            return f"Error: {e}"

    # ============================================
    # Tool 2: skills_ls - List files/directories
    # ============================================

    @mcp.tool()
    def skills_ls(
        path: str = Field(
            default="",
            description="Path to list. Supports: 'skills', 'workspace', or specific paths"
        ),
    ) -> str:
        """List files and directories.

        Virtual Paths:
        - ""              : List workspace root (user's mounted directory)
        - "skills"        : List all available skills
        - "skills/<name>" : List files in a specific skill
        - "workspace/xxx" : List in workspace directory
        - "./xxx" or "xxx": Relative to workspace
        - "/absolute"     : Direct path (if accessible)

        Examples:
        - skills_ls() - list workspace (user's project root)
        - skills_ls(path="skills") - list all skills
        - skills_ls(path="skills/gcd-calculator") - list skill files
        - skills_ls(path="src") - list src/ in workspace
        """
        actual_path = path if isinstance(path, str) else ""
        
        # Special case: list all skills
        if actual_path == "skills":
            skills = skill_manager.discover_skills()
            if not skills:
                return "No skills found"
            lines = []
            for skill in skills:
                lines.append(f"  {skill.name}/  - {skill.description}")
            return f"Skills ({len(skills)}):\n" + "\n".join(lines)
        
        # Handle skills/<skill-name> paths specially (need skill manager)
        if actual_path.startswith("skills/"):
            parts = actual_path.split("/")
            skill_name = parts[1]
            skill_path = skill_manager.get_skill_path(skill_name)
            if not skill_path:
                return f"Error: skill '{skill_name}' not found"
            remaining = "/".join(parts[2:])
            target = skill_path / remaining if remaining else skill_path
        else:
            # Use generic path resolution
            target = resolve_path(actual_path)
        
        if not target.exists():
            # Provide helpful error for empty workspace
            if actual_path == "" or actual_path == "workspace":
                return (
                    f"Workspace directory is empty or not mounted.\n"
                    f"(resolved to: {target})\n\n"
                    "To mount your project, use:\n"
                    "  docker run -v /your/project:/workspace ..."
                )
            return f"Error: path '{actual_path}' not found (resolved to: {target})"
        
        if not target.is_dir():
            return f"Error: '{actual_path}' is not a directory"
        
        # List contents
        items = []
        for item in sorted(target.iterdir()):
            if item.name.startswith("."):
                continue
            if item.is_dir():
                items.append(f"  {item.name}/")
            else:
                size = item.stat().st_size
                items.append(f"  {item.name}  ({size} bytes)")
        
        if not items:
            return f"Directory '{actual_path or 'workspace'}' is empty"
        
        return f"Contents of '{actual_path or 'workspace'}' ({len(items)} items):\n" + "\n".join(items)

    # ============================================
    # Tool 3: skills_read - Read file content
    # ============================================

    @mcp.tool()
    def skills_read(
        path: str = Field(description="Path to the file to read"),
    ) -> str:
        """Read file content (text files only).

        Virtual Paths:
        - "skills/<name>/SKILL.md"        : Read skill instructions
        - "skills/<name>/scripts/xxx.py"  : Read skill script
        - "workspace/<filename>"          : Read from workspace
        - "./<filename>" or "<filename>"  : Relative to workspace
        - "/absolute/path"                : Direct path (if accessible)

        Examples:
        - skills_read(path="skills/gcd-calculator/SKILL.md")
        - skills_read(path="src/main.py")  # Read from workspace
        - skills_read(path="workspace/output/result.txt")
        """
        # Handle skills/ paths specially (need skill manager for path resolution)
        if path.startswith("skills/"):
            parts = path.split("/")
            if len(parts) < 2:
                return "Error: invalid skill path"
            skill_name = parts[1]
            skill_path = skill_manager.get_skill_path(skill_name)
            if not skill_path:
                return f"Error: skill '{skill_name}' not found"
            
            remaining = "/".join(parts[2:]) if len(parts) > 2 else "SKILL.md"
            target = skill_path / remaining
        else:
            # Use generic path resolution for all other paths
            target = resolve_path(path)
        
        if not target.exists():
            return f"Error: file '{path}' not found (resolved to: {target})"
        
        if target.is_dir():
            return f"Error: '{path}' is a directory, use skills_ls() instead"
        
        try:
            content = target.read_text(encoding="utf-8")
            return content
        except UnicodeDecodeError:
            return f"Error: '{path}' is not a text file (binary file)"
        except Exception as e:
            return f"Error reading file: {e}"

    # ============================================
    # Tool 4: skills_write - Write/modify file
    # ============================================

    @mcp.tool()
    def skills_write(
        path: str = Field(description="Path to the file to write"),
        content: str = Field(description="Content to write to the file"),
    ) -> str:
        """Write or modify a file.

        Creates parent directories automatically if they don't exist.
        
        Virtual Paths:
        - "skills/<name>/<file>"          : Write to skill directory
        - "workspace/<filename>"          : Write to workspace
        - "./<filename>" or "<filename>"  : Relative to workspace
        - "/absolute/path"                : Direct path (if writable)

        Examples:
        - skills_write(path="skills/my-skill/scripts/run.py", content="print('hello')")
        - skills_write(path="output/result.txt", content="result data")
        - skills_write(path="workspace/data.json", content="{...}")
        """
        # Handle skills/ paths specially (need skill manager for path resolution)
        if path.startswith("skills/"):
            parts = path.split("/")
            if len(parts) < 3:
                return "Error: invalid skill path, need at least skills/<name>/<file>"
            skill_name = parts[1]
            skill_path = skill_manager.get_skill_path(skill_name)
            if not skill_path:
                return f"Error: skill '{skill_name}' not found"
            
            remaining = "/".join(parts[2:])
            target = skill_path / remaining
        else:
            # Use generic path resolution
            target = resolve_path(path)
        
        try:
            # Ensure parent directory exists
            target.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            target.write_text(content, encoding="utf-8")
            
            return f"Successfully wrote {len(content)} bytes to '{path}'"
        except PermissionError:
            return f"Error: permission denied writing to '{path}'. Check mount permissions."
        except Exception as e:
            return f"Error writing file: {e}"

    # ============================================
    # Tool 5: skills_create - Create new skill
    # ============================================

    @mcp.tool()
    def skills_create(
        name: str = Field(description="Skill name (lowercase letters, numbers, hyphens)"),
        description: str = Field(description="One-line description of what the skill does"),
        instructions: str = Field(description="Markdown instructions for SKILL.md"),
    ) -> str:
        """Create a new skill.

        Creates a skill directory with SKILL.md containing the provided metadata
        and instructions.

        Naming rules:
        - Use lowercase letters, numbers, and hyphens only
        - Must start with a letter
        - Examples: "code-reviewer", "data-analyzer", "gcd-calculator"

        Examples:
        - skills_create(name="my-tool", description="Does X", instructions="# Usage\\n...")
        """
        import re
        
        # Validate skill name
        if not re.match(r"^[a-z][a-z0-9-]*$", name):
            return (
                f"Error: invalid name '{name}'. "
                "Use lowercase letters, numbers, and hyphens only."
            )
        
        # Determine skill directory
        skill_dir = SKILLS_DIR / name
        if not SKILLS_DIR.exists():
            # Try built-in skills directory
            builtin_dir = Path(__file__).parent.parent / "skills"
            if builtin_dir.exists():
                skill_dir = builtin_dir / name
        
        if skill_dir.exists():
            return f"Error: skill '{name}' already exists at {skill_dir}"
        
        try:
            # Create skill directory
            skill_dir.mkdir(parents=True, exist_ok=True)
            
            # Format SKILL.md content
            import yaml
            frontmatter = {"name": name, "description": description}
            frontmatter_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
            skill_content = f"---\n{frontmatter_str}---\n\n{instructions}"
            
            # Write SKILL.md
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(skill_content, encoding="utf-8")
            
            return json.dumps({
                "status": "success",
                "name": name,
                "path": str(skill_dir),
                "uri": f"skill://{name}",
            }, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Error creating skill: {e}"

    # ============================================
    # Tool 6: skills_bash - Execute shell command
    # ============================================

    @mcp.tool()
    async def skills_bash(
        command: str = Field(description="Shell command to execute"),
        timeout: int = Field(default=60, description="Maximum execution time in seconds"),
        cwd: str = Field(default="", description="Working directory (supports virtual paths)"),
    ) -> str:
        """Execute a shell command in the execution environment.

        This is for general commands like rm, grep, mkdir, etc.
        For running skill scripts, use skills_run() instead.

        Working Directory (cwd):
        - ""              : Workspace root (user's project, default)
        - "skills/<name>" : Inside a skill directory
        - "workspace/xxx" : Inside workspace subdirectory
        - "./xxx" or "xxx": Relative to workspace
        - "/absolute"     : Direct path

        Examples:
        - skills_bash(command="ls -la")  # List workspace (user's project)
        - skills_bash(command="python main.py")  # Run in workspace
        - skills_bash(command="grep -r 'pattern' .", cwd="src")
        - skills_bash(command="npm install", cwd="workspace")
        """
        actual_timeout = timeout if isinstance(timeout, int) else 60
        
        # Determine working directory using path resolution
        if cwd and isinstance(cwd, str):
            if cwd.startswith("skills/"):
                # Handle skills/ paths with skill manager
                parts = cwd.split("/")
                skill_name = parts[1]
                skill_path = skill_manager.get_skill_path(skill_name)
                if skill_path:
                    remaining = "/".join(parts[2:]) if len(parts) > 2 else ""
                    work_dir = skill_path / remaining if remaining else skill_path
                else:
                    return f"Error: skill '{skill_name}' not found"
            else:
                # Use generic path resolution
                work_dir = resolve_path(cwd)
        else:
            work_dir = WORKSPACE_DIR
        
        if not work_dir.exists():
            try:
                work_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                return f"Error: cannot access working directory '{cwd}' (resolved to: {work_dir})"
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(work_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=actual_timeout,
            )
            
            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                if stderr_text:
                    output += f"\n[stderr]\n{stderr_text}"
            
            if process.returncode != 0:
                return f"Exit code: {process.returncode}\n{output}"
            
            return output if output else "(no output)"
            
        except asyncio.TimeoutError:
            return f"Command timed out after {actual_timeout} seconds"
        except Exception as e:
            return f"Error: {e}"

    return {
        "skill_manager": skill_manager,
        "workspace_dir": WORKSPACE_DIR,
        "skills_dir": SKILLS_DIR,
    }


def _create_skill_manager(skills_dirs: list[str] | None = None) -> SkillManager:
    """Create a SkillManager for Docker environment.
    
    Args:
        skills_dirs: Optional list of additional skill directories
        
    Returns:
        Configured SkillManager instance
    """
    # Collect skill directories
    skill_paths: list[Path] = []
    
    # Add external skills directory (volume mount)
    if SKILLS_DIR.exists():
        skill_paths.append(SKILLS_DIR)
    
    # Add workspace skills
    workspace_skills = WORKSPACE_DIR / ".skills"
    if workspace_skills.exists():
        skill_paths.append(workspace_skills)
    
    # Add user-provided directories
    if skills_dirs:
        for dir_path in skills_dirs:
            p = Path(dir_path)
            if p.exists() and p.is_dir():
                skill_paths.append(p)
    
    # Create skill manager
    builtin_dir = Path(__file__).parent.parent / "skills"
    return SkillManager(
        skills_dirs=skill_paths if skill_paths else None,
        builtin_skills_dir=builtin_dir,
    )

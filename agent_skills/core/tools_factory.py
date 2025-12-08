import asyncio
import re
import json
import yaml
from pathlib import Path
from typing import List, Optional, Any, Dict

from langchain_core.tools import tool, BaseTool, StructuredTool
from pydantic import BaseModel, Field

from agent_skills.core.docker_runner import DockerRunner
from agent_skills.core.skill_manager import SkillManager, SKILL_FILE_NAME

# Constants matching MCP implementation
WORKSPACE_MOUNT_POINT = "/workspace"
SKILLS_MOUNT_POINT = "/skills"

def create_docker_tools(
    runner: DockerRunner, 
    local_skill_manager: SkillManager,
    workspace_mount: str = WORKSPACE_MOUNT_POINT,
    skills_mount: str = SKILLS_MOUNT_POINT
) -> List[BaseTool]:
    """
    Deprecated helper. Use `DockerToolFactory.get_tools()` instead.
    """
    raise NotImplementedError("create_docker_tools is deprecated; use DockerToolFactory.get_tools().")

class DockerToolFactory:
    def __init__(self, runner: DockerRunner, skill_manager: SkillManager, host_workspace: Path, host_skills: Path):
        self.runner = runner
        self.skill_manager = skill_manager
        self.host_workspace = host_workspace.resolve()
        self.host_skills = host_skills.resolve()

    def resolve_host_path(self, path: str) -> Path:
        """Resolve virtual path to Host filesystem path."""
        path = path.strip()
        
        if not path or path == "/" or path == "workspace":
            return self.host_workspace

        if path.startswith("skills/"):
            # Handle specific skill lookup
            parts = path.split("/")
            if len(parts) >= 2:
                skill_name = parts[1]
                # Ask SkillManager where this skill is located on Host
                info = self.skill_manager.find_skill(skill_name)
                if info:
                    skill_root = Path(info.path)
                    remaining = "/".join(parts[2:])
                    return skill_root / remaining
            
            # Fallback to main skills dir
            return self.host_skills / path[7:]

        if path.startswith("workspace/"):
            return self.host_workspace / path[10:]

        if path.startswith("./"):
            return self.host_workspace / path[2:]

        if path.startswith("/"):
            # If absolute, check if it falls within allowed mounts
            p = Path(path)
            # This is tricky because the user might give a Container Absolute Path (e.g. /workspace/foo)
            # and we need to map it to Host.
            # If it starts with /workspace, map to host workspace
            if str(p).startswith(WORKSPACE_MOUNT_POINT):
                rel = str(p)[len(WORKSPACE_MOUNT_POINT):].lstrip("/")
                return self.host_workspace / rel
            if str(p).startswith(SKILLS_MOUNT_POINT):
                rel = str(p)[len(SKILLS_MOUNT_POINT):].lstrip("/")
                return self.host_skills / rel
            
            # If it's a real Host Absolute Path (user error?), allow if strictly enabled?
            # Better to assume it's a Container Path we can't map easily if it's outside mounts.
            # Fallback: Treat as relative to workspace to be safe?
            # Or just return it if we trust the user knows what they are doing locally.
            # Let's default to blocking unknown absolute paths or mapping them to workspace.
            return self.host_workspace / path.lstrip("/")

        return self.host_workspace / path

    def resolve_container_path(self, path: str) -> str:
        """Resolve virtual path to Container filesystem path."""
        path = path.strip()
        
        if not path or path == "/" or path == "workspace":
            return WORKSPACE_MOUNT_POINT

        if path.startswith("skills/"):
            return f"{SKILLS_MOUNT_POINT}/{path[7:]}"

        if path.startswith("workspace/"):
            return f"{WORKSPACE_MOUNT_POINT}/{path[10:]}"

        if path.startswith("./"):
            return f"{WORKSPACE_MOUNT_POINT}/{path[2:]}"
        
        if path.startswith("/"):
            return path # Absolute path in container

        return f"{WORKSPACE_MOUNT_POINT}/{path}"

    def get_tools(self) -> List[BaseTool]:
        
        @tool
        def skills_ls(path: str = "") -> str:
            """List files and directories.
            Virtual Paths:
            - "" or "workspace": List workspace root
            - "skills": List all available skills
            - "skills/<name>": List files in a specific skill
            """
            # Special case: list skills
            if path.strip() == "skills":
                skills = self.skill_manager.discover_skills()
                if not skills:
                    return "No skills found"
                lines = []
                for skill in skills:
                    lines.append(f"  {skill.name}/  - {skill.description}")
                return f"Skills ({len(skills)}):\n" + "\n".join(lines)

            target = self.resolve_host_path(path)
            
            if not target.exists():
                return f"Error: path '{path}' not found (resolved to: {target})"
            
            if not target.is_dir():
                return f"Error: '{path}' is not a directory"

            items = []
            try:
                for item in sorted(target.iterdir()):
                    if item.name.startswith("."):
                        continue
                    if item.is_dir():
                        items.append(f"  {item.name}/")
                    else:
                        size = item.stat().st_size
                        items.append(f"  {item.name}  ({size} bytes)")
            except Exception as e:
                 return f"Error listing directory: {e}"

            if not items:
                return f"Directory '{path or 'workspace'}' is empty"
            
            return f"Contents of '{path or 'workspace'}' ({len(items)} items):\n" + "\n".join(items)

        @tool
        def skills_read(path: str) -> str:
            """Read file content (text files only)."""
            target = self.resolve_host_path(path)
            
            if not target.exists():
                return f"Error: file '{path}' not found"
            
            if target.is_dir():
                return f"Error: '{path}' is a directory"
            
            try:
                return target.read_text(encoding="utf-8")
            except Exception as e:
                return f"Error reading file: {e}"

        @tool
        def skills_write(path: str, content: str) -> str:
            """Write or modify a file."""
            target = self.resolve_host_path(path)
            
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return f"Successfully wrote {len(content)} bytes to '{path}'"
            except Exception as e:
                return f"Error writing file: {e}"

        @tool
        def skills_create(name: str, description: str, instructions: str) -> str:
            """Create a new skill."""
            # Use SkillManager directly as it handles validation and creation logic perfectly
            # Note: SkillManager writes to Host FS, which is what we want.
            # We just need to make sure the Runner can see it (via mounts).
            
            result = self.skill_manager.create(name, description, instructions)
            if result.status == "error":
                return f"Error: {result.message}"
            return json.dumps(result.data, indent=2, ensure_ascii=False)

        @tool
        def skills_run(name: str, command: str, timeout: int = 120) -> str:
            """Run a command inside a skill directory."""
            # 1. Resolve path in Container
            skill_path_container = f"{SKILLS_MOUNT_POINT}/{name}"
            # Verify skill exists (using Local Manager)
            if not self.skill_manager.find_skill(name):
                 return f"Error: skill '{name}' not found"
            
            # 2. Check for pyproject.toml (Need to check on HOST or inside CONTAINER?)
            # Checking on Host is faster.
            host_skill_path = self.resolve_host_path(f"skills/{name}")
            pyproject_path = host_skill_path / "scripts" / "pyproject.toml"
            
            if pyproject_path.exists():
                # Logic: Use uv isolation
                # We must construct the command to run `uv sync` then `uv run` inside the container
                # The MCP implementation does this via `asyncio.create_subprocess` inside the container context.
                # Here we are outside. We can send a combined command to `docker exec`.
                
                # Command construction:
                # "cd /skills/name/scripts && uv sync --quiet && uv run <cmd>"
                
                adjusted_command = command
                if "scripts/" in command:
                     adjusted_command = command.replace("scripts/", "")

                # Construct shell command chain
                # Note: 'uv' should be in the path of the container image
                
                # We need to set Environment vars to avoid using VIRTUAL_ENV from parent if any
                # But docker exec starts fresh usually.
                
                full_cmd = f"bash -c 'cd scripts && uv sync --quiet && uv run {adjusted_command}'"
                
                output, code = self.runner.run_command(full_cmd, cwd=skill_path_container, timeout=timeout)
                
                if code != 0:
                    return f"Exit code: {code}\n{output}"
                return output

            else:
                # Direct execution
                output, code = self.runner.run_command(command, cwd=skill_path_container, timeout=timeout)
                if code != 0:
                    return f"Exit code: {code}\n{output}"
                return output

        @tool
        def skills_bash(command: str, cwd: str = "", timeout: int = 60) -> str:
            """Execute shell command in workspace."""
            # Resolve cwd to Container Path
            work_dir = self.resolve_container_path(cwd)
            
            output, code = self.runner.run_command(command, cwd=work_dir, timeout=timeout)
            
            if code != 0:
                return f"Exit code: {code}\n{output}"
            return output if output else "(no output)"

        return [skills_ls, skills_read, skills_write, skills_create, skills_run, skills_bash]



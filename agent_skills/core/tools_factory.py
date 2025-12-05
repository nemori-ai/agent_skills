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
    Create LangChain tools that execute via Docker but mirror the MCP logic.
    """

    # Helper for path resolution (Logic ported from mcp/tools.py)
    # But adapted: We resolve to CONTAINER paths for execution, and HOST paths for read/write if mounted.
    # Actually, for consistency with `DockerRunner`, let's do this:
    # - Execution (run, bash): Use container paths.
    # - File Ops (read, write, ls): Since we have the volume mounted locally, 
    #   we can perform these operations on the HOST directly for speed and simplicity.
    #   BUT, to be strictly "Docker-backed" and avoid permission issues (e.g. root owned files created by docker),
    #   we should probably use `ls` inside docker.
    #   However, for read/write, local is fine if permissions allow.
    #   Let's stick to Local FS for File Ops where possible as it's the "Middleware" philosophy (Host controls).
    #   Wait, if the container creates a file as root, Host might not be able to edit it.
    #   
    #   Let's check the MCP implementation:
    #   It uses `pathlib` and `os` calls.
    #   
    #   Strategy:
    #   - `skills_ls`: Use Docker `ls` or Host `os.listdir`? Host is better if volumes are consistent.
    #   - `skills_run`: Docker exec.
    #   - `skills_bash`: Docker exec.
    
    #   Let's define a path resolver that maps Virtual Path -> Host Path.
    
    # We need to access the host paths that are mounted.
    # We can ask the runner for them, or pass them in. 
    # DockerRunner stores `self.workspace_dir` (container path), but we need the Host path.
    # In `DockerSkillsMiddleware` we will pass the host paths to `runner.start()`.
    # Let's assume we can get them or they are consistent.
    
    # Actually, `DockerRunner` takes host paths in `start()`. 
    # Let's assume the `local_skill_manager` knows the Host paths.
    
    # SKILLS_DIR is inside local_skill_manager._skills_dirs (list).
    # WORKSPACE_DIR needs to be passed in.
    
    # Wait, `resolve_path` in MCP handles virtual paths: `skills/`, `workspace/`.
    # We need to replicate this.
    
    def resolve_virtual_path(path: str, context: str = "host") -> Path:
        """
        Resolve virtual path to absolute path.
        context: "host" or "container"
        """
        path = path.strip()
        
        # Base paths
        if context == "host":
            # Finding the correct skills dir on host is tricky if there are multiple.
            # We'll use the first one or the one matching the skill name.
            # For simplicity, let's assume one main skills dir for now or rely on SkillManager for specific skills.
            # But `workspace` is easy.
            # We need to know the Host Workspace Path. 
            # It's not passed here explicitly. We should pass it to `create_docker_tools`.
            # Let's fix signature.
            pass
        else:
            # Container Context
            base_skills = Path(skills_mount)
            base_workspace = Path(workspace_mount)
            
            if not path or path == "/" or path == "workspace":
                return base_workspace
            
            if path.startswith("skills/"):
                return base_skills / path[7:]
            
            if path.startswith("workspace/"):
                return base_workspace / path[10:]
                
            if path.startswith("./"):
                return base_workspace / path[2:]
                
            if path.startswith("/"):
                return Path(path)
                
            return base_workspace / path

    # We need the Host Workspace Path to perform local I/O.
    # Let's assume `runner` has it or we pass it.
    # Let's rely on Docker execution for EVERYTHING (`ls`, `cat`) to be safe about permissions 
    # and strictly follow the "Docker Backend" promise.
    # Use `runner.run_command` for ls, read (cat), write (echo/tee).
    # Wait, `write` with `echo` is dangerous for escaping.
    # Better to write to a temp file on host and `docker cp`? 
    # Or just write to the Host Volume directly? 
    # Writing to Host Volume directly is the most robust way if we have permissions.
    
    # Let's use Host I/O for Read/Write/Ls because `agent_skills` is designed with volumes in mind.
    # We just need to know the HOST paths.
    
    # We need a `HostPathResolver` class or similar.
    pass

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



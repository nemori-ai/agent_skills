import asyncio
import re
import json
import yaml
import posixpath
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
    def __init__(
        self, 
        runner: DockerRunner, 
        skill_manager: SkillManager, 
        host_workspace: Optional[Path],  # Now optional
        host_skills: Path
    ):
        self.runner = runner
        self.skill_manager = skill_manager
        self.host_workspace = host_workspace.resolve() if host_workspace else None
        self.host_skills = host_skills.resolve()
        
    @property
    def has_workspace(self) -> bool:
        """Check if workspace is configured."""
        return self.host_workspace is not None

    def _get_default_root(self) -> Path:
        """Get default root directory (workspace if available, else skills)."""
        if self.host_workspace is not None:
            return self.host_workspace
        return self.host_skills
    
    def _ensure_within_root(self, root: Path, target: Path, *, user_input: str) -> Path:
        """Resolve and ensure target stays within root (blocks ../ and symlink escapes)."""
        root_resolved = root.resolve(strict=False)
        target_resolved = target.resolve(strict=False)
        if not target_resolved.is_relative_to(root_resolved):
            raise ValueError(
                "越界访问被禁止。\n"
                f"输入: {user_input}\n"
                f"允许根目录: {root_resolved}\n"
                f"解析后路径: {target_resolved}"
            )
        return target_resolved
    
    def _resolve_in_root(self, root: Path, rel: str, *, user_input: str) -> Path:
        """Resolve a subpath under root, preventing escapes."""
        if not rel:
            return root.resolve(strict=False)
        return self._ensure_within_root(root, root / rel, user_input=user_input)
    
    def _resolve_in_skill_root(self, skill_root: Path, remaining: str, *, user_input: str) -> Path:
        """Resolve a subpath within a specific skill directory, preventing escapes."""
        if not remaining:
            return skill_root.resolve(strict=False)
        return self._ensure_within_root(skill_root, skill_root / remaining, user_input=user_input)

    def resolve_host_path(self, path: str) -> Path:
        """Resolve virtual path to Host filesystem path."""
        path = path.strip()
        
        if not path or path == "/":
            return self._get_default_root().resolve(strict=False)
        
        if path == "workspace":
            if self.host_workspace is None:
                raise ValueError("Workspace not configured. Use skills/ paths instead.")
            return self.host_workspace.resolve(strict=False)

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
                    return self._resolve_in_skill_root(skill_root, remaining, user_input=path)
            
            # Fallback to main skills dir
            return self._resolve_in_root(self.host_skills, path[7:], user_input=path)

        if path.startswith("workspace/"):
            if self.host_workspace is None:
                raise ValueError("Workspace not configured. Use skills/ paths instead.")
            return self._resolve_in_root(self.host_workspace, path[10:], user_input=path)

        if path.startswith("./"):
            root = self._get_default_root()
            return self._resolve_in_root(root, path[2:], user_input=path)

        if path.startswith("/"):
            # If absolute, check if it falls within allowed mounts
            p = Path(path)
            # Map container paths to host paths
            if str(p).startswith(WORKSPACE_MOUNT_POINT):
                if self.host_workspace is None:
                    raise ValueError("Workspace not configured. Use /skills paths instead.")
                rel = str(p)[len(WORKSPACE_MOUNT_POINT):].lstrip("/")
                return self._resolve_in_root(self.host_workspace, rel, user_input=path)
            if str(p).startswith(SKILLS_MOUNT_POINT):
                rel = str(p)[len(SKILLS_MOUNT_POINT):].lstrip("/")
                return self._resolve_in_root(self.host_skills, rel, user_input=path)
            
            # Unknown absolute path - map to default root
            root = self._get_default_root()
            return self._resolve_in_root(root, path.lstrip("/"), user_input=path)

        root = self._get_default_root()
        return self._resolve_in_root(root, path, user_input=path)

    def resolve_container_path(self, path: str) -> str:
        """Resolve virtual path to Container filesystem path."""
        path = path.strip()
        
        # Default mount: workspace if available, else skills
        default_mount = WORKSPACE_MOUNT_POINT if self.has_workspace else SKILLS_MOUNT_POINT
        
        if not path or path == "/":
            return default_mount
        
        if path == "workspace":
            if not self.has_workspace:
                return SKILLS_MOUNT_POINT
            return WORKSPACE_MOUNT_POINT

        if path.startswith("skills/"):
            raw = f"{SKILLS_MOUNT_POINT}/{path[7:]}"
            norm = posixpath.normpath(raw)
            if norm == SKILLS_MOUNT_POINT or norm.startswith(f"{SKILLS_MOUNT_POINT}/"):
                return norm
            raise ValueError(f"cwd 越界访问被禁止: {path}")

        if path.startswith("workspace/"):
            if not self.has_workspace:
                raw = f"{SKILLS_MOUNT_POINT}/{path[10:]}"
                norm = posixpath.normpath(raw)
                if norm == SKILLS_MOUNT_POINT or norm.startswith(f"{SKILLS_MOUNT_POINT}/"):
                    return norm
                raise ValueError(f"cwd 越界访问被禁止: {path}")
            raw = f"{WORKSPACE_MOUNT_POINT}/{path[10:]}"
            norm = posixpath.normpath(raw)
            if norm == WORKSPACE_MOUNT_POINT or norm.startswith(f"{WORKSPACE_MOUNT_POINT}/"):
                return norm
            raise ValueError(f"cwd 越界访问被禁止: {path}")

        if path.startswith("./"):
            raw = f"{default_mount}/{path[2:]}"
            norm = posixpath.normpath(raw)
            if norm == default_mount or norm.startswith(f"{default_mount}/"):
                return norm
            raise ValueError(f"cwd 越界访问被禁止: {path}")
        
        if path.startswith("/"):
            norm = posixpath.normpath(path)
            allowed = (
                norm == WORKSPACE_MOUNT_POINT
                or norm.startswith(f"{WORKSPACE_MOUNT_POINT}/")
                or norm == SKILLS_MOUNT_POINT
                or norm.startswith(f"{SKILLS_MOUNT_POINT}/")
            )
            if allowed:
                return norm
            raise ValueError(
                "不允许使用容器内外部绝对路径作为 cwd。请使用 workspace/... 或 skills/... 的虚拟路径。"
            )

        raw = f"{default_mount}/{path}"
        norm = posixpath.normpath(raw)
        if norm == default_mount or norm.startswith(f"{default_mount}/"):
            return norm
        raise ValueError(f"cwd 越界访问被禁止: {path}")

    def get_tools(self) -> List[BaseTool]:
        
        @tool
        def skills_ls(path: str = "") -> str:
            """List files and directories.
            Virtual Paths:
            - "skills": List all available skills
            - "skills/<name>": List files in a specific skill
            - "" or "workspace": List workspace root (if configured)
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

            try:
                target = self.resolve_host_path(path)
            except ValueError as e:
                return f"Error: {e}"
            
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

            default_name = "workspace" if self.has_workspace else "skills"
            if not items:
                return f"Directory '{path or default_name}' is empty"
            
            return f"Contents of '{path or default_name}' ({len(items)} items):\n" + "\n".join(items)

        @tool
        def skills_read(path: str) -> str:
            """Read file content (text files only)."""
            try:
                target = self.resolve_host_path(path)
            except ValueError as e:
                return f"Error: {e}"
            
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
            try:
                target = self.resolve_host_path(path)
            except ValueError as e:
                return f"Error: {e}"
            
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

        def _check_output_path_warning(command: str) -> str:
            """Check if command has output path not in /workspace/ and return warning."""
            import shlex
            warnings = []
            
            try:
                parts = shlex.split(command)
                for i, part in enumerate(parts):
                    # Check for -o or --output flags
                    if part in ("-o", "--output") and i + 1 < len(parts):
                        output_path = parts[i + 1]
                        if not output_path.startswith("/workspace"):
                            warnings.append(
                                f"⚠️ WARNING: Output path '{output_path}' is not in /workspace/. "
                                f"Files should be saved to /workspace/ to keep skills directory clean. "
                                f"Consider using: -o /workspace/{output_path.lstrip('/')}"
                            )
                    # Check for combined format like -o=path or --output=path
                    elif part.startswith("-o=") or part.startswith("--output="):
                        output_path = part.split("=", 1)[1]
                        if not output_path.startswith("/workspace"):
                            warnings.append(
                                f"⚠️ WARNING: Output path '{output_path}' is not in /workspace/. "
                                f"Files should be saved to /workspace/ to keep skills directory clean."
                            )
            except Exception:
                pass  # Ignore parsing errors
            
            return "\n".join(warnings)

        @tool
        def skills_run(name: str, command: str, timeout: int = 120) -> str:
            """Run a command inside a skill directory."""
            # 1. Resolve path in Container
            skill_path_container = f"{SKILLS_MOUNT_POINT}/{name}"
            # Verify skill exists (using Local Manager)
            if not self.skill_manager.find_skill(name):
                 return f"Error: skill '{name}' not found"
            
            # Check for output path warnings
            path_warning = _check_output_path_warning(command)
            
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
                # Prepend warning if exists
                if path_warning:
                    return f"{path_warning}\n\n{output}"
                return output

            else:
                # Direct execution
                output, code = self.runner.run_command(command, cwd=skill_path_container, timeout=timeout)
                if code != 0:
                    return f"Exit code: {code}\n{output}"
                # Prepend warning if exists
                if path_warning:
                    return f"{path_warning}\n\n{output}"
                return output if output else "(no output)"

        @tool
        def skills_bash(command: str, cwd: str = "", timeout: int = 60) -> str:
            """Execute shell command in workspace."""
            # Resolve cwd to Container Path
            try:
                work_dir = self.resolve_container_path(cwd)
            except ValueError as e:
                return f"Error: {e}"
            
            output, code = self.runner.run_command(command, cwd=work_dir, timeout=timeout)
            
            if code != 0:
                return f"Exit code: {code}\n{output}"
            return output if output else "(no output)"

        return [skills_ls, skills_read, skills_write, skills_create, skills_run, skills_bash]



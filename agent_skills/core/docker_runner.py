import docker
from docker import errors as docker_errors
import tarfile
import io
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

class DockerRunner:
    """
    Manages a persistent Docker container for skill execution.
    Acts as a bridge between the host middleware and the containerized environment.
    """
    
    def __init__(
        self, 
        image_name: str = "agent-skills:latest", 
        container_name: str = "agent-skills-runner",
        workspace_dir: str = "/workspace",
        skills_dir: str = "/skills"
    ):
        self.client = docker.from_env()
        self.image_name = image_name
        self.container_name = container_name
        self.workspace_dir = workspace_dir
        self.skills_dir = skills_dir
        self.container = None
        self._started = False

    def start(
        self, 
        host_skills_path: str, 
        host_workspace_path: Optional[str] = None,
        extra_mounts: Optional[Dict[str, str]] = None,
    ):
        """
        Start or reuse the Docker container with appropriate volume mounts.
        
        Args:
            host_skills_path: Path to skills directory on host (required, mounted to /skills)
            host_workspace_path: Optional path to workspace on host (mounted to /workspace).
                                If None, /workspace won't be mounted. (deprecated, use extra_mounts)
            extra_mounts: Optional dict of additional mounts {host_path: container_path}.
                         Example: {"/Users": "/Users"} to mount macOS home directory.
        """
        host_skills = Path(host_skills_path).resolve()
        host_workspace = Path(host_workspace_path).resolve() if host_workspace_path else None
        
        # Ensure directories exist
        if host_workspace:
            host_workspace.mkdir(parents=True, exist_ok=True)
        if not host_skills.exists():
             # Warning: Skills dir usually should exist, but we can proceed if it doesn't
             pass

        # Fast path: already started and running
        if self._started and self.container:
            try:
                self.container.reload()
                if self.container.status == "running":
                    return self.container
            except Exception:
                # fall through to recreate
                pass

        try:
            # Check if container exists
            try:
                self.container = self.client.containers.get(self.container_name)
                self.container.reload()
                if self.container.status != "running":
                    self.container.start()
            except docker_errors.NotFound:
                # Build volume mounts
                volumes = {
                    str(host_skills): {"bind": self.skills_dir, "mode": "rw"},
                }
                if host_workspace:
                    volumes[str(host_workspace)] = {"bind": self.workspace_dir, "mode": "rw"}
                
                # Add extra mounts (e.g., {"/Users": "/Users"})
                if extra_mounts:
                    for host_path, container_path in extra_mounts.items():
                        resolved_host = str(Path(host_path).resolve())
                        volumes[resolved_host] = {"bind": container_path, "mode": "rw"}
                
                # Create new container
                self.container = self.client.containers.run(
                    self.image_name,
                    name=self.container_name,
                    detach=True,
                    tty=True,  # Keep it running
                    volumes=volumes,
                    command="tail -f /dev/null",  # Keep alive
                    entrypoint="/usr/bin/tail -f /dev/null",  # Override entrypoint to prevent MCP server from starting
                    environment={
                        "SKILLS_WORKSPACE": self.workspace_dir if host_workspace else "",
                        "SKILLS_DIR": self.skills_dir,
                        "PYTHONUNBUFFERED": "1",
                    },
                )

            # Wait a moment for container to be ready
            time.sleep(1)
            self._started = True
            return self.container

        except Exception as e:
            self._started = False
            raise RuntimeError(f"Failed to start Docker container: {e}")

    def stop(self, remove: bool = False, timeout: int = 10):
        """
        Stop the managed container. Optionally remove it.
        Idempotent: safe to call multiple times.
        """
        if not self.container:
            self._started = False
            return

        try:
            self.container.reload()
            if self.container.status == "running":
                try:
                    self.container.stop(timeout=timeout)
                except Exception:
                    # best-effort stop
                    pass

            if remove:
                try:
                    self.container.remove(force=False)
                    self.container = None
                except Exception:
                    pass
        finally:
            self._started = False

    def close(self):
        """Alias for stop(remove=False) to allow explicit shutdown."""
        self.stop(remove=False)

    def run_command(
        self, 
        command: str, 
        cwd: Optional[str] = None, 
        env: Optional[dict] = None,
        timeout: int = 120
    ) -> Tuple[str, int]:
        """
        Run a command inside the container.
        Returns (output, exit_code).
        """
        if not self.container:
            raise RuntimeError("Container not initialized. Call start() first.")

        # Default to skills_dir if no cwd specified (workspace may not be mounted)
        workdir = cwd if cwd else self.skills_dir
        environment = env if env else {}

        # Exec run
        # Wrap command in bash to support redirection and shell features
        # Similar to how asyncio.create_subprocess_shell works
        # Note: We use single quotes for bash -c '...' so we need to escape single quotes in command
        safe_command = command.replace("'", "'\\''")
        shell_cmd = f"bash -c '{safe_command}'"

        try:
            exec_result = self.container.exec_run(
                cmd=shell_cmd,
                workdir=workdir,
                environment=environment,
                # user="root", # defaulting to root or image default
            )
            
            output = exec_result.output.decode("utf-8", errors="replace")
            exit_code = exec_result.exit_code
            
            return output, exit_code
            
        except Exception as e:
            return f"Docker execution error: {e}", 1

    def is_dir(self, path: str) -> bool:
        """Check if path is a directory inside container."""
        if not self.container:
            return False
        # Use stat command inside linux container
        code, _ = self.container.exec_run(f"test -d {path}")
        return code == 0

    def file_exists(self, path: str) -> bool:
        """Check if file exists inside container."""
        if not self.container:
            return False
        code, _ = self.container.exec_run(f"test -e {path}")
        return code == 0


import docker
import tarfile
import io
import time
from pathlib import Path
from typing import Optional, Tuple

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

    def start(self, host_workspace_path: str, host_skills_path: str):
        """
        Start or reuse the Docker container with appropriate volume mounts.
        """
        host_workspace = Path(host_workspace_path).resolve()
        host_skills = Path(host_skills_path).resolve()
        
        # Ensure directories exist
        host_workspace.mkdir(parents=True, exist_ok=True)
        if not host_skills.exists():
             # Warning: Skills dir usually should exist, but we can proceed if it doesn't
             pass

        try:
            # Check if container exists
            try:
                self.container = self.client.containers.get(self.container_name)
                if self.container.status != "running":
                    self.container.start()
            except docker.errors.NotFound:
                # Create new container
                self.container = self.client.containers.run(
                    self.image_name,
                    name=self.container_name,
                    detach=True,
                    tty=True, # Keep it running
                    volumes={
                        str(host_workspace): {'bind': self.workspace_dir, 'mode': 'rw'},
                        str(host_skills): {'bind': self.skills_dir, 'mode': 'rw'} # Skills might need write if we allow creating skills
                    },
                    command="tail -f /dev/null", # Keep alive
                    entrypoint="/usr/bin/tail -f /dev/null", # Override entrypoint to prevent MCP server from starting
                    environment={
                        "SKILLS_WORKSPACE": self.workspace_dir,
                        "SKILLS_DIR": self.skills_dir,
                        "PYTHONUNBUFFERED": "1"
                    }
                )
                
            # Wait a moment for container to be ready
            time.sleep(1)
            
        except Exception as e:
            raise RuntimeError(f"Failed to start Docker container: {e}")

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

        workdir = cwd if cwd else self.workspace_dir
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


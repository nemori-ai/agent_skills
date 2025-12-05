from abc import ABC, abstractmethod
from typing import Tuple, Optional, Any

class ExecutionBackend(ABC):
    """
    Abstract base class for execution environments (Local vs Docker).
    Allows tools to be agnostic of where they are running.
    """
    
    @abstractmethod
    def run_command(self, command: str, cwd: Optional[str] = None, env: Optional[dict] = None, timeout: int = 120) -> Tuple[str, int]:
        """Run a shell command."""
        pass

    @abstractmethod
    def is_dir(self, path: str) -> bool:
        """Check if path is a directory."""
        pass
    
    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        pass

    # Note: Read/Write can be done via standard Python file I/O for Local,
    # but for Docker we might need special handling if we don't assume shared volume mounting for everything.
    # However, since we mount volumes in DockerRunner, we *can* technically use local file I/O 
    # if we map the paths correctly. But for purity, we might want exec-based read/write 
    # or just assume the Middleware has access to the mounted paths locally.
    # 
    # Decision: The MCP implementation uses `pathlib` directly because it runs INSIDE the container.
    # Our middleware runs OUTSIDE. 
    # For `skills_read` and `skills_write`, if we have volume mounts, we can use local FS!
    # This is much faster and simpler.
    # 
    # So we need a method to translate "Container Path" -> "Host Path".
    
    @abstractmethod
    def resolve_to_host_path(self, container_path: str) -> str:
        """Resolve a container execution path to a host filesystem path."""
        pass


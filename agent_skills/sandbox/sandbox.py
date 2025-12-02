"""Sandbox implementation for security and path isolation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from collections.abc import Sequence


class SandboxConfig(BaseModel):
    """Configuration for the sandbox."""

    # Root workspace directory - all operations are restricted to this
    workspace_root: str = Field(default_factory=lambda: os.getcwd())

    # Files/directories that cannot be accessed
    blacklist: list[str] = Field(
        default_factory=lambda: [
            ".git",
            ".env",
            ".env.*",
            "*.pem",
            "*.key",
            "*_secret*",
            "*password*",
            ".ssh",
        ]
    )

    # Commands that are not allowed to execute
    command_blacklist: list[str] = Field(
        default_factory=lambda: [
            # Destructive commands
            "rm -rf /",
            "rm -rf /*",
            "rm -rf ~",
            "mkfs",
            "dd if=/dev/zero",
            "dd of=/dev/",
            "> /dev/sda",
            "> /dev/nvme",
            # Fork bomb and similar
            ":(){:|:&};:",
            ":(){ :|:& };:",
            # Privilege escalation
            "sudo",
            "su ",
            "su\n",
            "doas",
            # Dangerous permission changes
            "chmod 777 /",
            "chmod -R 777 /",
            "chown -R",
            # System modification
            "shutdown",
            "reboot",
            "init 0",
            "init 6",
            "systemctl poweroff",
            "systemctl reboot",
            # Network attacks (if network is disabled)
            # These are checked separately based on allow_network config
        ]
    )

    # Whether to allow network access in bash commands
    allow_network: bool = False

    # Whether to allow write operations
    allow_write: bool = True

    # Maximum file size for read/write operations (in bytes)
    max_file_size: int = 10 * 1024 * 1024  # 10 MB

    # Whether to inherit PATH from current environment (includes Python, etc.)
    inherit_path: bool = True

    # Additional paths to add to PATH (e.g., custom Python installations)
    extra_paths: list[str] = Field(default_factory=list)


class Sandbox:
    """Security sandbox for file and command operations."""

    def __init__(self, config: SandboxConfig | None = None):
        """Initialize sandbox with configuration."""
        self.config = config or SandboxConfig()
        self._workspace_path = Path(self.config.workspace_root).resolve()

    @property
    def workspace_root(self) -> Path:
        """Get the workspace root path."""
        return self._workspace_path

    def resolve_path(self, path: str) -> Path:
        """
        Resolve a path relative to workspace root.

        Args:
            path: The path to resolve (can be relative or absolute)

        Returns:
            Resolved absolute path

        Raises:
            PermissionError: If path is outside workspace or blacklisted
        """
        # Handle relative and absolute paths
        if os.path.isabs(path):
            resolved = Path(path).resolve()
        else:
            resolved = (self._workspace_path / path).resolve()

        # Security check: ensure path is within workspace
        self._check_path_allowed(resolved)

        return resolved

    def _check_path_allowed(self, path: Path) -> None:
        """
        Check if a path is allowed to be accessed.

        Args:
            path: The resolved path to check

        Raises:
            PermissionError: If path is not allowed
        """
        # Check if within workspace
        try:
            path.relative_to(self._workspace_path)
        except ValueError:
            raise PermissionError(
                f"Access denied: path '{path}' is outside workspace '{self._workspace_path}'"
            )

        # Check against blacklist patterns
        path_str = str(path)
        for pattern in self.config.blacklist:
            if self._matches_pattern(path_str, path.name, pattern):
                raise PermissionError(
                    f"Access denied: path '{path}' matches blacklist pattern '{pattern}'"
                )

    def _matches_pattern(self, full_path: str, name: str, pattern: str) -> bool:
        """Check if a path matches a blacklist pattern."""
        import fnmatch

        # Check if the pattern matches the filename
        if fnmatch.fnmatch(name, pattern):
            return True

        # Check if any component of the path matches
        parts = Path(full_path).parts
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True

        return False

    def check_write_allowed(self) -> None:
        """
        Check if write operations are allowed.

        Raises:
            PermissionError: If write is not allowed
        """
        if not self.config.allow_write:
            raise PermissionError("Write operations are not allowed in this sandbox")

    def check_file_size(self, size: int) -> None:
        """
        Check if file size is within limits.

        Args:
            size: File size in bytes

        Raises:
            ValueError: If file exceeds size limit
        """
        if size > self.config.max_file_size:
            raise ValueError(
                f"File size {size} exceeds maximum allowed size {self.config.max_file_size}"
            )

    def validate_command(self, command: str) -> None:
        """
        Validate a shell command against security rules.

        Args:
            command: The command to validate

        Raises:
            PermissionError: If command is not allowed
        """
        cmd_lower = command.lower().strip()

        # Check against command blacklist
        for blacklisted in self.config.command_blacklist:
            if blacklisted.lower() in cmd_lower:
                raise PermissionError(
                    f"Command contains blacklisted pattern: '{blacklisted}'"
                )

        # Check for path traversal attempts (escaping sandbox)
        # Block commands that try to access parent directories
        path_traversal_patterns = [
            "..",        # Parent directory
            "/../",      # Path traversal in middle
            "../",       # Start with parent
            "/..",       # End with parent
        ]
        for pattern in path_traversal_patterns:
            if pattern in command:
                raise PermissionError(
                    f"Path traversal not allowed: '{pattern}' detected in command. "
                    "You can only access files within the skills directory."
                )

        # Block absolute paths (except for common safe commands)
        # This prevents accessing /etc/passwd, /home/user, etc.
        import re
        # Match absolute paths like /etc, /home, /usr but not command flags like -la
        abs_path_match = re.search(r'(?<![a-zA-Z0-9_-])/(?:etc|home|usr|var|tmp|root|opt|bin|sbin|lib|dev|proc|sys|boot|mnt|media|srv)[/\s]?', command)
        if abs_path_match:
            raise PermissionError(
                f"Absolute system paths not allowed. "
                "You can only access files within the skills directory."
            )

    def get_safe_env(self) -> dict[str, str]:
        """
        Get a safe environment for command execution.

        Returns:
            Dictionary of environment variables
        """
        # Build PATH
        if self.config.inherit_path and "PATH" in os.environ:
            # Inherit PATH from current environment (includes Python, venv, etc.)
            path_value = os.environ["PATH"]
        else:
            # Use minimal PATH
            path_value = "/usr/local/bin:/usr/bin:/bin"

        # Add extra paths if configured
        if self.config.extra_paths:
            extra = ":".join(self.config.extra_paths)
            path_value = f"{extra}:{path_value}"

        # Start with environment
        safe_env = {
            "PATH": path_value,
            "HOME": str(self._workspace_path),
            "PWD": str(self._workspace_path),
            "LANG": "en_US.UTF-8",
        }

        # Optionally inherit some safe variables from current environment
        safe_inherit = ["TERM", "USER", "SHELL"]
        for var in safe_inherit:
            if var in os.environ:
                safe_env[var] = os.environ[var]

        # Inherit virtual environment variables if present
        venv_vars = ["VIRTUAL_ENV", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"]
        for var in venv_vars:
            if var in os.environ:
                safe_env[var] = os.environ[var]

        return safe_env

    def list_allowed_paths(self, paths: Sequence[str]) -> list[Path]:
        """
        Filter a list of paths, returning only allowed ones.

        Args:
            paths: Sequence of paths to filter

        Returns:
            List of allowed resolved paths
        """
        allowed: list[Path] = []
        for p in paths:
            try:
                resolved = self.resolve_path(p)
                allowed.append(resolved)
            except PermissionError:
                continue
        return allowed


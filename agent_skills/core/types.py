"""Core type definitions for agent skills."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolStatus(str, Enum):
    """Status of a tool execution."""

    SUCCESS = "success"
    ERROR = "error"


class ToolResult(BaseModel):
    """Base result type for all tool operations."""

    status: ToolStatus = ToolStatus.SUCCESS
    message: str = ""
    data: Any = None

    @classmethod
    def success(cls, message: str = "", data: Any = None) -> ToolResult:
        """Create a success result."""
        return cls(status=ToolStatus.SUCCESS, message=message, data=data)

    @classmethod
    def error(cls, message: str, data: Any = None) -> ToolResult:
        """Create an error result."""
        return cls(status=ToolStatus.ERROR, message=message, data=data)


class FileInfo(BaseModel):
    """Information about a file or directory."""

    name: str
    path: str
    is_dir: bool = False
    size: int = 0
    modified: datetime | None = None
    permissions: str = ""

    def __str__(self) -> str:
        """Format file info for ls output."""
        if self.is_dir:
            return f"drwxr-xr-x  {self.name}/"
        return f"-rw-r--r--  {self.size:>8}  {self.name}"


class EditResult(BaseModel):
    """Result of a file edit operation."""

    status: ToolStatus = ToolStatus.SUCCESS
    message: str = ""
    path: str = ""
    replacements: int = 0
    old_content: str | None = None
    new_content: str | None = None

    @classmethod
    def success(
        cls,
        path: str,
        replacements: int,
        message: str = "",
    ) -> EditResult:
        """Create a success result."""
        return cls(
            status=ToolStatus.SUCCESS,
            message=message or f"Successfully made {replacements} replacement(s)",
            path=path,
            replacements=replacements,
        )

    @classmethod
    def error(cls, message: str, path: str = "") -> EditResult:
        """Create an error result."""
        return cls(status=ToolStatus.ERROR, message=message, path=path)


class CommandResult(BaseModel):
    """Result of a command execution."""

    status: ToolStatus = ToolStatus.SUCCESS
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    command: str = ""
    duration_ms: int = 0
    timed_out: bool = False
    pid: int | None = None

    @property
    def output(self) -> str:
        """Combined stdout and stderr output."""
        parts: list[str] = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(f"[stderr]\n{self.stderr}")
        return "\n".join(parts) if parts else ""

    @classmethod
    def success(
        cls,
        stdout: str = "",
        stderr: str = "",
        command: str = "",
        exit_code: int = 0,
        duration_ms: int = 0,
    ) -> CommandResult:
        """Create a success result."""
        return cls(
            status=ToolStatus.SUCCESS,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            command=command,
            duration_ms=duration_ms,
        )

    @classmethod
    def error(
        cls,
        stderr: str,
        exit_code: int = 1,
        command: str = "",
        stdout: str = "",
        timed_out: bool = False,
    ) -> CommandResult:
        """Create an error result."""
        return cls(
            status=ToolStatus.ERROR,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            command=command,
            timed_out=timed_out,
        )


class SkillInfo(BaseModel):
    """Information about a skill.

    Used for skill discovery and MCP Resource registration.
    The name and description are preloaded as resource metadata,
    while full content is read on-demand via read_resource().
    """

    name: str
    description: str = ""
    path: str = ""
    version: str = "1.0.0"

    @property
    def uri(self) -> str:
        """Get the MCP Resource URI for this skill."""
        return f"skill://{self.name}"

    def __str__(self) -> str:
        """Format skill info for listing."""
        return f"{self.name}: {self.description}"


class BackgroundTask(BaseModel):
    """Information about a background task."""

    pid: int
    command: str
    started_at: datetime = Field(default_factory=datetime.now)
    cwd: str = ""

    def __str__(self) -> str:
        """Format background task info."""
        return f"[{self.pid}] {self.command}"


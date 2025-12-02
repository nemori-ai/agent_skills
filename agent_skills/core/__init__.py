"""Core modules for agent skills.

Primary modules (used by MCP tools):
- Executor: Command execution (bash, bg, jobs, kill)
- SkillManager: Skill management (list, create, load, validate)

Internal modules (kept for programmatic use):
- FileSystem: File operations (cat, ls, find, grep, etc.)
- Editor: File editing (sed, write, append, insert)
"""

from agent_skills.core.editor import Editor
from agent_skills.core.executor import Executor
from agent_skills.core.filesystem import FileSystem
from agent_skills.core.skill_manager import SkillManager
from agent_skills.core.types import (
    CommandResult,
    EditResult,
    FileInfo,
    SkillInfo,
    ToolResult,
)

__all__ = [
    # Types
    "CommandResult",
    "EditResult",
    "FileInfo",
    "SkillInfo",
    "ToolResult",
    # Primary modules
    "Executor",
    "SkillManager",
    # Internal modules (kept for programmatic use)
    "Editor",
    "FileSystem",
]


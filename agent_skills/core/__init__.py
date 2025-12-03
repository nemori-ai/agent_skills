"""Core modules for agent skills.

Primary modules:
- SkillManager: Skill management (discover, create, validate)
- types: Type definitions (SkillInfo, ToolResult, etc.)
"""

from agent_skills.core.skill_manager import SkillManager
from agent_skills.core.types import (
    CommandResult,
    FileInfo,
    SkillInfo,
    ToolResult,
    ToolStatus,
)

__all__ = [
    # Types
    "CommandResult",
    "FileInfo",
    "SkillInfo",
    "ToolResult",
    "ToolStatus",
    # Primary modules
    "SkillManager",
]

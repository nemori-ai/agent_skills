"""Skill Manager module for managing AI agent skills.

Provides: skill discovery, creation, and validation for MCP Resources.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from agent_skills.core.types import SkillInfo, ToolResult, ToolStatus


# Skill file name constants
SKILL_FILE_NAME = "SKILL.md"

# Default pyproject.toml template for skill scripts
PYPROJECT_TOML_TEMPLATE = '''[project]
name = "{skill_name}-scripts"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.uv]
managed = true
'''


class SkillManager:
    """Manager for AI agent skills.

    Skills are folders containing a SKILL.md file with YAML frontmatter
    and markdown instructions that teach an agent how to complete specific tasks.

    Skills are exposed as MCP Resources for progressive disclosure:
    - Skill metadata (name, description) is preloaded for agent awareness
    - Full SKILL.md content is read on-demand via read_resource()
    """

    def __init__(
        self,
        skills_dirs: list[Path] | None = None,
        builtin_skills_dir: Path | None = None,
    ) -> None:
        """
        Initialize SkillManager.

        Args:
            skills_dirs: List of directories to search for skills (prioritized over builtin)
            builtin_skills_dir: Built-in skills directory (default: agent_skills/skills/)
        """
        # Default skills directories
        self._skills_dirs: list[Path] = []

        # Set built-in skills directory for creating new skills
        self._builtin_skills_dir = builtin_skills_dir or (Path(__file__).parent.parent / "skills")

        # IMPORTANT: Add user-provided directories FIRST for priority
        # This ensures mounted/external directories take precedence over builtin
        # so that files written to external dirs are persisted and discoverable
        if skills_dirs:
            for dir_path in skills_dirs:
                if dir_path.exists() and dir_path.is_dir():
                    self._skills_dirs.append(dir_path)

        # Add built-in skills directory LAST (lower priority)
        # This allows builtin skills to be overridden by external ones
        if self._builtin_skills_dir.exists():
            self._skills_dirs.append(self._builtin_skills_dir)

    def discover_skills(self) -> list[SkillInfo]:
        """
        Discover all available skills in skills directories.

        This is the public API for getting skill metadata,
        used by MCP Resource registration.

        Returns:
            List of SkillInfo with name, description, and path
        """
        skills: list[SkillInfo] = []
        seen_names: set[str] = set()

        for skills_dir in self._skills_dirs:
            if not skills_dir.exists():
                continue

            for item in skills_dir.iterdir():
                if not item.is_dir():
                    continue

                skill_file = item / SKILL_FILE_NAME
                if not skill_file.exists():
                    continue

                try:
                    content = skill_file.read_text(encoding="utf-8")
                    parsed = self._parse_skill_file(content)

                    if parsed:
                        frontmatter, _ = parsed
                        name = str(frontmatter.get("name", item.name))

                        if name not in seen_names:
                            seen_names.add(name)
                            skills.append(
                                SkillInfo(
                                    name=name,
                                    description=str(frontmatter.get("description", "")),
                                    path=str(item),
                                )
                            )
                except Exception:
                    continue

        return sorted(skills, key=lambda s: s.name)

    def find_skill(self, name: str) -> SkillInfo | None:
        """
        Find a skill by name.

        Args:
            name: Name of the skill to find

        Returns:
            SkillInfo if found, None otherwise
        """
        for skill in self.discover_skills():
            if skill.name == name:
                return skill
        return None

    def read_skill_content(self, name: str) -> str | None:
        """
        Read the full content of a skill's SKILL.md file.

        Args:
            name: Name of the skill to read

        Returns:
            Full SKILL.md content or None if not found
        """
        skill = self.find_skill(name)
        if skill is None:
            return None

        skill_file = Path(skill.path) / SKILL_FILE_NAME
        if not skill_file.exists():
            return None

        return skill_file.read_text(encoding="utf-8")

    def get_skill_path(self, name: str) -> Path | None:
        """
        Get the absolute directory path of a skill.

        Args:
            name: Name of the skill

        Returns:
            Path object to the skill directory or None if not found
        """
        skill = self.find_skill(name)
        if skill is None:
            return None
        return Path(skill.path)

    def create(
        self,
        name: str,
        description: str,
        instructions: str,
        target_dir: Path | None = None,
    ) -> ToolResult:
        """
        Create a new skill.

        Args:
            name: Unique skill name (lowercase, hyphens for spaces)
            description: Clear description of what the skill does
            instructions: Markdown content with instructions for the agent
            target_dir: Directory to create the skill in (defaults to builtin skills dir)

        Returns:
            ToolResult with the created skill info
        """
        try:
            # Validate skill name
            if not re.match(r"^[a-z][a-z0-9-]*$", name):
                return ToolResult.error(
                    f"skill create: invalid name '{name}'. "
                    "Use lowercase letters, numbers, and hyphens only."
                )

            # Determine where to create the skill
            skill_dir = (target_dir or self._builtin_skills_dir) / name

            # Check if skill already exists
            if skill_dir.exists():
                return ToolResult.error(
                    f"skill create: skill '{name}' already exists at {skill_dir}"
                )

            # Create skill directory
            skill_dir.mkdir(parents=True, exist_ok=True)

            # Create SKILL.md content
            skill_content = self._format_skill_file(name, description, instructions)

            # Write SKILL.md
            skill_file = skill_dir / SKILL_FILE_NAME
            skill_file.write_text(skill_content, encoding="utf-8")

            # Add parent directory to search paths so the skill is immediately discoverable
            parent_dir = skill_dir.parent
            if parent_dir not in self._skills_dirs:
                self._skills_dirs.append(parent_dir)

            return ToolResult.success(
                message=f"skill create: created skill '{name}' at {skill_dir}",
                data={
                    "name": name,
                    "path": str(skill_dir),
                    "file": str(skill_file),
                    "uri": f"skill://{name}",
                },
            )

        except Exception as e:
            return ToolResult.error(f"skill create: {e}")

    def validate(self, path: str) -> ToolResult:
        """
        Validate a skill's format and structure.

        Args:
            path: Path to the skill directory or SKILL.md file

        Returns:
            ToolResult with validation results
        """
        try:
            resolved = Path(path).resolve()

            # Determine skill file path
            if resolved.is_dir():
                skill_file = resolved / SKILL_FILE_NAME
            elif resolved.name == SKILL_FILE_NAME:
                skill_file = resolved
            else:
                return ToolResult.error(
                    f"skill validate: expected directory or {SKILL_FILE_NAME} file"
                )

            if not skill_file.exists():
                return ToolResult.error(
                    f"skill validate: {SKILL_FILE_NAME} not found at {path}"
                )

            # Read and parse
            content = skill_file.read_text(encoding="utf-8")
            parsed = self._parse_skill_file(content)

            errors: list[str] = []
            warnings: list[str] = []

            if parsed is None:
                errors.append("Invalid YAML frontmatter")
            else:
                frontmatter, instructions = parsed

                # Check required fields
                if "name" not in frontmatter:
                    errors.append("Missing required field: name")
                else:
                    name_value = str(frontmatter["name"])
                    if not re.match(r"^[a-z][a-z0-9-]*$", name_value):
                        errors.append(
                            "Invalid name format (use lowercase, numbers, hyphens)"
                        )

                if "description" not in frontmatter:
                    errors.append("Missing required field: description")
                else:
                    desc_value = str(frontmatter["description"])
                    if len(desc_value) < 10:
                        warnings.append("Description is very short")

                # Check instructions
                if not instructions.strip():
                    errors.append("Empty instructions content")
                elif len(instructions) < 50:
                    warnings.append("Instructions are very short")

                # Check for common patterns
                if "## " not in instructions and "# " not in instructions:
                    warnings.append("No headings found in instructions")

            # Format result
            result_lines: list[str] = []
            if errors:
                result_lines.append("❌ Validation failed:")
                for err in errors:
                    result_lines.append(f"  • Error: {err}")
                for warn in warnings:
                    result_lines.append(f"  • Warning: {warn}")
                return ToolResult(
                    status=ToolStatus.ERROR,
                    message="Validation failed",
                    data="\n".join(result_lines),
                )
            else:
                result_lines.append("✓ Validation passed")
                for warn in warnings:
                    result_lines.append(f"  • Warning: {warn}")
                return ToolResult.success(
                    message="Validation passed",
                    data="\n".join(result_lines),
                )

        except Exception as e:
            return ToolResult.error(f"skill validate: {e}")

    def add_file(self, name: str, file_path: str, content: str) -> ToolResult:
        """
        Add a file to a skill directory.

        If adding a Python script (.py) to the scripts/ directory and no
        pyproject.toml exists yet, a default pyproject.toml will be
        automatically created for uv-based dependency management.

        Args:
            name: Name of the skill
            file_path: Relative path of the file within the skill directory
            content: Content of the file

        Returns:
            ToolResult indicating success or failure
        """
        skill_path = self.get_skill_path(name)
        if skill_path is None:
            return ToolResult.error(f"skill add_file: skill '{name}' not found")

        try:
            # Validate relative path prevents escaping skill dir
            target_file = (skill_path / file_path).resolve()
            
            # Security check: ensure target_file is inside skill_path
            if not str(target_file).startswith(str(skill_path.resolve())):
                return ToolResult.error(
                    f"skill add_file: path '{file_path}' attempts to access outside skill directory"
                )

            # Ensure parent directory exists
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            target_file.write_text(content, encoding="utf-8")
            
            # Auto-generate pyproject.toml for Python scripts in scripts/ directory
            pyproject_created = False
            if file_path.endswith(".py") and file_path.startswith("scripts/"):
                pyproject_created = self._ensure_scripts_pyproject(skill_path, name)
            
            result_data: dict[str, Any] = {
                "skill": name,
                "file": str(target_file),
                "size": len(content)
            }
            
            message = f"skill add_file: added '{file_path}' to skill '{name}'"
            if pyproject_created:
                result_data["pyproject_created"] = True
                message += " (auto-created scripts/pyproject.toml for uv environment)"
            
            return ToolResult.success(message=message, data=result_data)
        except Exception as e:
            return ToolResult.error(f"skill add_file: {e}")
    
    def _ensure_scripts_pyproject(self, skill_path: Path, skill_name: str) -> bool:
        """
        Ensure scripts/pyproject.toml exists for uv-based dependency management.

        Args:
            skill_path: Path to the skill directory
            skill_name: Name of the skill (used in pyproject.toml)

        Returns:
            True if pyproject.toml was created, False if it already existed
        """
        scripts_dir = skill_path / "scripts"
        pyproject_path = scripts_dir / "pyproject.toml"
        
        if pyproject_path.exists():
            return False
        
        # Create scripts directory if needed
        scripts_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate and write pyproject.toml
        pyproject_content = PYPROJECT_TOML_TEMPLATE.format(skill_name=skill_name)
        pyproject_path.write_text(pyproject_content, encoding="utf-8")
        
        return True

    def list_files(self, name: str) -> ToolResult:
        """
        List all files in a skill directory.

        Args:
            name: Name of the skill

        Returns:
            ToolResult with list of files
        """
        skill_path = self.get_skill_path(name)
        if skill_path is None:
            return ToolResult.error(f"skill list_files: skill '{name}' not found")

        try:
            files: list[str] = []
            for item in skill_path.rglob("*"):
                if item.is_file() and item.name != ".DS_Store":
                    rel_path = item.relative_to(skill_path)
                    files.append(str(rel_path))
            
            files.sort()
            return ToolResult.success(
                message=f"Found {len(files)} files in skill '{name}'",
                data=files
            )
        except Exception as e:
            return ToolResult.error(f"skill list_files: {e}")

    def read_file(self, name: str, file_path: str) -> ToolResult:
        """
        Read a specific file from a skill directory.

        Args:
            name: Name of the skill
            file_path: Relative path of the file to read

        Returns:
            ToolResult with file content
        """
        skill_path = self.get_skill_path(name)
        if skill_path is None:
            return ToolResult.error(f"skill read_file: skill '{name}' not found")

        try:
            target_file = (skill_path / file_path).resolve()
            
            # Security check
            if not str(target_file).startswith(str(skill_path.resolve())):
                return ToolResult.error(
                    f"skill read_file: path '{file_path}' attempts to access outside skill directory"
                )
            
            if not target_file.exists():
                return ToolResult.error(f"skill read_file: file '{file_path}' not found in skill '{name}'")
                
            content = target_file.read_text(encoding="utf-8")
            return ToolResult.success(
                message=f"Read {len(content)} bytes from '{file_path}'",
                data=content
            )
        except Exception as e:
            return ToolResult.error(f"skill read_file: {e}")

    def _parse_skill_file(self, content: str) -> tuple[dict[str, Any], str] | None:
        """
        Parse a SKILL.md file into frontmatter and content.

        Args:
            content: The raw file content

        Returns:
            Tuple of (frontmatter dict, markdown content) or None if invalid
        """
        # Match YAML frontmatter
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            return None

        try:
            frontmatter_str, markdown = match.groups()
            frontmatter: dict[str, Any] = yaml.safe_load(frontmatter_str)
            if not isinstance(frontmatter, dict):
                return None
            return frontmatter, markdown.strip()
        except yaml.YAMLError:
            return None

    def _format_skill_file(
        self,
        name: str,
        description: str,
        instructions: str,
    ) -> str:
        """
        Format a SKILL.md file content.

        Args:
            name: Skill name
            description: Skill description
            instructions: Markdown instructions

        Returns:
            Formatted SKILL.md content
        """
        frontmatter = {
            "name": name,
            "description": description,
        }
        # allow_unicode=True to prevent Chinese characters from being escaped
        frontmatter_str = yaml.dump(
            frontmatter, 
            default_flow_style=False, 
            allow_unicode=True,
        )

        return f"---\n{frontmatter_str}---\n\n{instructions}"

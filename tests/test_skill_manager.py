"""Tests for SkillManager module."""

from __future__ import annotations

from pathlib import Path


from agent_skills.core.skill_manager import SKILL_FILE_NAME, SkillManager
from agent_skills.core.types import ToolStatus


class TestSkillDiscover:
    """Tests for skill discovery."""

    def test_discover_skills(
        self, skill_manager: SkillManager, temp_workspace: Path
    ) -> None:
        """Test discovering skills."""
        # Create a skill
        skills_dir = temp_workspace / "skills" / "test-skill"
        skills_dir.mkdir(parents=True)
        skill_file = skills_dir / SKILL_FILE_NAME
        skill_file.write_text(
            """---
name: test-skill
description: A test skill for discovery
---

# Test Skill

These are the instructions.
"""
        )

        skills = skill_manager.discover_skills()
        assert len(skills) >= 1

        # Find the test skill
        skill_names = [s.name for s in skills]
        assert "test-skill" in skill_names

        # Check skill info
        test_skill = next(s for s in skills if s.name == "test-skill")
        assert test_skill.description == "A test skill for discovery"
        assert test_skill.uri == "skill://test-skill"

    def test_find_skill(
        self, skill_manager: SkillManager, temp_workspace: Path
    ) -> None:
        """Test finding a specific skill."""
        # Create a skill
        skills_dir = temp_workspace / "skills" / "findable-skill"
        skills_dir.mkdir(parents=True)
        skill_file = skills_dir / SKILL_FILE_NAME
        skill_file.write_text(
            """---
name: findable-skill
description: A skill that can be found
---

# Findable Skill
"""
        )

        skill = skill_manager.find_skill("findable-skill")
        assert skill is not None
        assert skill.name == "findable-skill"
        assert skill.description == "A skill that can be found"

    def test_find_nonexistent_skill(self, skill_manager: SkillManager) -> None:
        """Test finding a nonexistent skill."""
        skill = skill_manager.find_skill("nonexistent-skill")
        assert skill is None


class TestSkillCreate:
    """Tests for skill create command."""

    def test_create_skill(
        self, skill_manager: SkillManager, temp_workspace: Path
    ) -> None:
        """Test creating a new skill."""
        result = skill_manager.create(
            name="my-skill",
            description="Does something useful",
            instructions="# My Skill\n\nInstructions here.",
            target_dir=temp_workspace / "skills",
        )

        assert result.status == ToolStatus.SUCCESS
        assert "my-skill" in result.message

        # Verify the skill was created
        skill_dir = temp_workspace / "skills" / "my-skill"
        assert skill_dir.exists()
        assert (skill_dir / SKILL_FILE_NAME).exists()

    def test_create_invalid_name(self, skill_manager: SkillManager) -> None:
        """Test creating a skill with invalid name."""
        result = skill_manager.create(
            name="Invalid Name",
            description="Test",
            instructions="Test",
        )
        assert result.status == ToolStatus.ERROR
        assert "invalid name" in result.message.lower()

    def test_create_duplicate(
        self, skill_manager: SkillManager, temp_workspace: Path
    ) -> None:
        """Test creating a duplicate skill."""
        target_dir = temp_workspace / "skills"

        # Create first skill
        skill_manager.create("my-skill", "Test", "Test", target_dir)

        # Try to create duplicate
        result = skill_manager.create("my-skill", "Test 2", "Test 2", target_dir)
        assert result.status == ToolStatus.ERROR
        assert "already exists" in result.message


class TestSkillReadContent:
    """Tests for reading skill content."""

    def test_read_skill_content(
        self, skill_manager: SkillManager, temp_workspace: Path
    ) -> None:
        """Test reading skill content."""
        # Create a skill
        skills_dir = temp_workspace / "skills" / "content-skill"
        skills_dir.mkdir(parents=True)
        skill_file = skills_dir / SKILL_FILE_NAME
        skill_file.write_text(
            """---
name: content-skill
description: A skill with content
---

# Content Skill

These instructions should be readable.
"""
        )

        content = skill_manager.read_skill_content("content-skill")
        assert content is not None
        assert "content-skill" in content
        assert "These instructions should be readable" in content

    def test_read_nonexistent_skill_content(self, skill_manager: SkillManager) -> None:
        """Test reading content of nonexistent skill."""
        content = skill_manager.read_skill_content("nonexistent")
        assert content is None


class TestSkillValidate:
    """Tests for skill validate command."""

    def test_validate_valid_skill(
        self, skill_manager: SkillManager, temp_workspace: Path
    ) -> None:
        """Test validating a valid skill."""
        skill_dir = temp_workspace / "valid-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / SKILL_FILE_NAME
        skill_file.write_text(
            """---
name: valid-skill
description: A valid skill with proper structure
---

# Valid Skill

## Overview

This skill does something useful.

## Instructions

1. Step one
2. Step two
"""
        )

        result = skill_manager.validate(str(skill_dir))
        assert result.status == ToolStatus.SUCCESS
        assert "passed" in result.message.lower()

    def test_validate_missing_name(
        self, skill_manager: SkillManager, temp_workspace: Path
    ) -> None:
        """Test validating a skill missing name field."""
        skill_dir = temp_workspace / "invalid-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / SKILL_FILE_NAME
        skill_file.write_text(
            """---
description: Missing name field
---

# Invalid Skill
"""
        )

        result = skill_manager.validate(str(skill_dir))
        assert result.status == ToolStatus.ERROR
        assert "name" in result.data.lower()

    def test_validate_missing_description(
        self, skill_manager: SkillManager, temp_workspace: Path
    ) -> None:
        """Test validating a skill missing description."""
        skill_dir = temp_workspace / "no-desc-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / SKILL_FILE_NAME
        skill_file.write_text(
            """---
name: no-desc
---

# No Description Skill
"""
        )

        result = skill_manager.validate(str(skill_dir))
        assert result.status == ToolStatus.ERROR


class TestSkillAddFile:
    """Tests for adding files to skills."""

    def test_add_file_to_skill(
        self, skill_manager: SkillManager, temp_workspace: Path
    ) -> None:
        """Test adding a file to a skill."""
        # Create a skill first
        skills_dir = temp_workspace / "skills" / "file-skill"
        skills_dir.mkdir(parents=True)
        skill_file = skills_dir / SKILL_FILE_NAME
        skill_file.write_text(
            """---
name: file-skill
description: A skill for file testing
---

# File Skill
"""
        )

        # Add a file
        result = skill_manager.add_file(
            name="file-skill",
            file_path="scripts/run.py",
            content="print('hello')",
        )

        assert result.status == ToolStatus.SUCCESS
        
        # Verify file was created
        script_file = skills_dir / "scripts" / "run.py"
        assert script_file.exists()
        assert script_file.read_text() == "print('hello')"

    def test_add_file_to_nonexistent_skill(self, skill_manager: SkillManager) -> None:
        """Test adding a file to a nonexistent skill."""
        result = skill_manager.add_file(
            name="nonexistent",
            file_path="test.txt",
            content="test",
        )
        assert result.status == ToolStatus.ERROR

    def test_add_file_rejects_path_traversal(
        self, skill_manager: SkillManager, temp_workspace: Path
    ) -> None:
        """Reject attempts to write outside a skill directory via ../ traversal."""
        # Create a skill first
        skills_dir = temp_workspace / "skills" / "safe-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / SKILL_FILE_NAME).write_text(
            """---
name: safe-skill
description: A skill for traversal testing
---

# Safe Skill
""",
            encoding="utf-8",
        )

        # Attempt to escape the skill directory
        result = skill_manager.add_file(
            name="safe-skill",
            file_path="../escaped.txt",
            content="nope",
        )
        assert result.status == ToolStatus.ERROR
        # Ensure the escaped file was NOT created
        assert not (temp_workspace / "skills" / "escaped.txt").exists()

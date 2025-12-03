"""Pytest configuration and fixtures for agent-skills tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from agent_skills.core.skill_manager import SkillManager


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Create a temporary workspace directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        yield workspace


@pytest.fixture
def skill_manager(temp_workspace: Path) -> SkillManager:
    """Create a SkillManager instance."""
    skills_dir = temp_workspace / "skills"
    skills_dir.mkdir()
    return SkillManager(
        skills_dirs=[skills_dir],
        builtin_skills_dir=skills_dir,  # Use temp dir as builtin for tests
    )


@pytest.fixture
def sample_file(temp_workspace: Path) -> Path:
    """Create a sample text file for testing."""
    file_path = temp_workspace / "sample.txt"
    file_path.write_text("line 1\nline 2\nline 3\nfoo bar baz\n")
    return file_path


@pytest.fixture
def sample_dir(temp_workspace: Path) -> Path:
    """Create a sample directory structure for testing."""
    # Create directories
    (temp_workspace / "subdir1").mkdir()
    (temp_workspace / "subdir2").mkdir()
    (temp_workspace / "subdir1" / "nested").mkdir()

    # Create files
    (temp_workspace / "file1.txt").write_text("content 1")
    (temp_workspace / "file2.py").write_text("print('hello')")
    (temp_workspace / "subdir1" / "file3.txt").write_text("content 3")
    (temp_workspace / "subdir1" / "nested" / "file4.txt").write_text("content 4")
    (temp_workspace / ".hidden").write_text("hidden content")

    return temp_workspace

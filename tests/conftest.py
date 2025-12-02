"""Pytest configuration and fixtures for agent-skills tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from agent_skills.core.editor import Editor
from agent_skills.core.executor import Executor
from agent_skills.core.filesystem import FileSystem
from agent_skills.core.skill_manager import SkillManager
from agent_skills.sandbox.sandbox import Sandbox, SandboxConfig


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Create a temporary workspace directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        yield workspace


@pytest.fixture
def sandbox(temp_workspace: Path) -> Sandbox:
    """Create a sandbox with the temporary workspace."""
    config = SandboxConfig(workspace_root=str(temp_workspace))
    return Sandbox(config)


@pytest.fixture
def filesystem(sandbox: Sandbox) -> FileSystem:
    """Create a FileSystem instance with the sandbox."""
    return FileSystem(sandbox)


@pytest.fixture
def editor(sandbox: Sandbox) -> Editor:
    """Create an Editor instance with the sandbox."""
    return Editor(sandbox)


@pytest.fixture
def executor(sandbox: Sandbox) -> Executor:
    """Create an Executor instance with the sandbox."""
    return Executor(sandbox)


@pytest.fixture
def skill_manager(sandbox: Sandbox, temp_workspace: Path) -> SkillManager:
    """Create a SkillManager instance."""
    skills_dir = temp_workspace / "skills"
    skills_dir.mkdir()
    return SkillManager(sandbox, [str(skills_dir)])


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


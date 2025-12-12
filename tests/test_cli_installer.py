"""Tests for CLI installer module."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_skills.cli.installer import (
    DEFAULT_SKILLS_DIR,
    INSTALLED_METADATA_FILE,
    SKILL_FILE_NAME,
    InstallResult,
    SkillInfo,
    SkillInstaller,
)


class TestSkillInstaller:
    """Tests for SkillInstaller class."""

    def test_init_default_dir(self) -> None:
        """Test default skills directory."""
        installer = SkillInstaller()
        assert installer.skills_dir == DEFAULT_SKILLS_DIR

    def test_init_custom_dir(self, tmp_path: Path) -> None:
        """Test custom skills directory."""
        installer = SkillInstaller(skills_dir=tmp_path)
        assert installer.skills_dir == tmp_path.resolve()

    def test_extract_repo_name_https(self) -> None:
        """Test extracting repo name from HTTPS URL."""
        installer = SkillInstaller()

        assert installer._extract_repo_name(
            "https://github.com/user/my-skill.git"
        ) == "my-skill"

        assert installer._extract_repo_name(
            "https://github.com/user/my-skill"
        ) == "my-skill"

        assert installer._extract_repo_name(
            "https://github.com/user/my-skill/"
        ) == "my-skill"

    def test_extract_repo_name_ssh(self) -> None:
        """Test extracting repo name from SSH URL."""
        installer = SkillInstaller()

        # Note: SSH format parsing might need adjustment
        assert installer._extract_repo_name(
            "git@github.com:user/my-skill.git"
        ) == "my-skill"


class TestSkillInstallerUninstall:
    """Tests for uninstall functionality."""

    def test_uninstall_existing_skill(self, tmp_path: Path) -> None:
        """Test uninstalling an existing skill."""
        installer = SkillInstaller(skills_dir=tmp_path)

        # Create a skill directory
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / SKILL_FILE_NAME).write_text("---\nname: test-skill\n---\n")

        result = installer.uninstall("test-skill")

        assert result.success is True
        assert "test-skill" in result.message
        assert not skill_dir.exists()

    def test_uninstall_nonexistent_skill(self, tmp_path: Path) -> None:
        """Test uninstalling a skill that doesn't exist."""
        installer = SkillInstaller(skills_dir=tmp_path)

        result = installer.uninstall("nonexistent-skill")

        assert result.success is False
        assert "not found" in result.message

    def test_uninstall_invalid_skill(self, tmp_path: Path) -> None:
        """Test uninstalling a directory without SKILL.md."""
        installer = SkillInstaller(skills_dir=tmp_path)

        # Create a directory without SKILL.md
        skill_dir = tmp_path / "not-a-skill"
        skill_dir.mkdir()

        result = installer.uninstall("not-a-skill")

        assert result.success is False
        assert "not a valid skill" in result.message


class TestSkillInstallerList:
    """Tests for list functionality."""

    def test_list_empty_directory(self, tmp_path: Path) -> None:
        """Test listing skills in empty directory."""
        installer = SkillInstaller(skills_dir=tmp_path)

        skills = installer.list_skills()

        assert skills == []

    def test_list_skills(self, tmp_path: Path) -> None:
        """Test listing skills."""
        installer = SkillInstaller(skills_dir=tmp_path)

        # Create some skills
        skill1 = tmp_path / "skill-a"
        skill1.mkdir()
        (skill1 / SKILL_FILE_NAME).write_text(
            "---\nname: skill-a\ndescription: First skill\n---\n"
        )

        skill2 = tmp_path / "skill-b"
        skill2.mkdir()
        (skill2 / SKILL_FILE_NAME).write_text(
            "---\nname: skill-b\ndescription: Second skill\n---\n"
        )

        skills = installer.list_skills()

        assert len(skills) == 2
        assert skills[0].name == "skill-a"
        assert skills[0].description == "First skill"
        assert skills[1].name == "skill-b"

    def test_list_installed_only(self, tmp_path: Path) -> None:
        """Test listing only installed skills."""
        installer = SkillInstaller(skills_dir=tmp_path)

        # Create a regular skill
        skill1 = tmp_path / "regular-skill"
        skill1.mkdir()
        (skill1 / SKILL_FILE_NAME).write_text("---\nname: regular-skill\n---\n")

        # Create an installed skill
        skill2 = tmp_path / "installed-skill"
        skill2.mkdir()
        (skill2 / SKILL_FILE_NAME).write_text("---\nname: installed-skill\n---\n")
        (skill2 / INSTALLED_METADATA_FILE).write_text(
            json.dumps({"source": "https://github.com/user/skill.git"})
        )

        # List all skills
        all_skills = installer.list_skills()
        assert len(all_skills) == 2

        # List only installed skills
        installed_skills = installer.list_skills(installed_only=True)
        assert len(installed_skills) == 1
        assert installed_skills[0].name == "installed-skill"
        assert installed_skills[0].is_installed is True


class TestSkillInstallerInstall:
    """Tests for install functionality (mocked git)."""

    def test_install_creates_metadata(self, tmp_path: Path) -> None:
        """Test that install creates metadata file."""
        installer = SkillInstaller(skills_dir=tmp_path)

        # Mock the git operations and use a real temp directory
        with patch.object(installer, "_run_git_command") as mock_git:
            with patch("tempfile.TemporaryDirectory") as mock_tmpdir:
                # Setup mock temp directory
                mock_tmp = tmp_path / "mock_tmp"
                mock_tmp.mkdir()
                mock_repo = mock_tmp / "repo"
                mock_repo.mkdir()

                # Create SKILL.md in mock repo
                (mock_repo / SKILL_FILE_NAME).write_text(
                    "---\nname: test-skill\ndescription: Test\n---\n"
                )

                # Configure mocks
                mock_tmpdir.return_value.__enter__.return_value = str(mock_tmp)
                mock_git.return_value = MagicMock(stdout="abc123456789\n")

                result = installer.install("https://github.com/user/test-skill.git")

                # Check result
                assert result.success is True

                # Check metadata was created
                skill_dir = tmp_path / "test-skill"
                assert skill_dir.exists()
                metadata_file = skill_dir / INSTALLED_METADATA_FILE
                assert metadata_file.exists()

                metadata = json.loads(metadata_file.read_text())
                assert metadata["source"] == "https://github.com/user/test-skill.git"

    def test_install_already_exists(self, tmp_path: Path) -> None:
        """Test installing a skill that already exists."""
        installer = SkillInstaller(skills_dir=tmp_path)

        # Create existing skill
        existing_skill = tmp_path / "my-skill"
        existing_skill.mkdir()
        (existing_skill / SKILL_FILE_NAME).write_text("---\nname: my-skill\n---\n")

        with patch.object(installer, "_run_git_command") as mock_git:
            with patch("tempfile.TemporaryDirectory") as mock_tmpdir:
                mock_tmp = tmp_path / "mock_tmp"
                mock_tmp.mkdir()
                mock_repo = mock_tmp / "repo"
                mock_repo.mkdir()
                (mock_repo / SKILL_FILE_NAME).write_text("---\nname: my-skill\n---\n")

                mock_tmpdir.return_value.__enter__.return_value = str(mock_tmp)
                mock_git.return_value = MagicMock(stdout="abc123\n")

                result = installer.install("https://github.com/user/my-skill.git")

                assert result.success is False
                assert "already exists" in result.message


class TestParseSkillFile:
    """Tests for SKILL.md parsing."""

    def test_parse_valid_frontmatter(self, tmp_path: Path) -> None:
        """Test parsing valid SKILL.md frontmatter."""
        installer = SkillInstaller(skills_dir=tmp_path)

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / SKILL_FILE_NAME).write_text(
            """---
name: test-skill
description: A test skill for testing
---

# Test Skill

Instructions here.
"""
        )

        result = installer._parse_skill_file(skill_dir)

        assert result["name"] == "test-skill"
        assert result["description"] == "A test skill for testing"

    def test_parse_missing_file(self, tmp_path: Path) -> None:
        """Test parsing when SKILL.md is missing."""
        installer = SkillInstaller(skills_dir=tmp_path)

        result = installer._parse_skill_file(tmp_path)

        assert result == {}

    def test_parse_no_frontmatter(self, tmp_path: Path) -> None:
        """Test parsing SKILL.md without frontmatter."""
        installer = SkillInstaller(skills_dir=tmp_path)

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / SKILL_FILE_NAME).write_text("# Just a markdown file\n")

        result = installer._parse_skill_file(skill_dir)

        assert result == {}


class TestSparseCheckout:
    """Tests for sparse checkout (--path) functionality."""

    def test_install_with_path_writes_metadata(self, tmp_path: Path) -> None:
        """Test that install with --path writes path to metadata."""
        installer = SkillInstaller(skills_dir=tmp_path)

        with patch.object(installer, "_clone_with_sparse_checkout") as mock_sparse:
            with patch.object(installer, "_get_current_commit", return_value="abc123"):
                with patch("tempfile.TemporaryDirectory") as mock_tmpdir:
                    mock_tmp = tmp_path / "mock_tmp"
                    mock_tmp.mkdir()
                    mock_repo = mock_tmp / "repo"
                    mock_repo.mkdir()

                    # Create the path structure
                    skill_path = mock_repo / ".claude" / "skills" / "my-skill"
                    skill_path.mkdir(parents=True)
                    (skill_path / SKILL_FILE_NAME).write_text(
                        "---\nname: my-skill\ndescription: Test\n---\n"
                    )

                    mock_tmpdir.return_value.__enter__.return_value = str(mock_tmp)
                    mock_sparse.return_value = None

                    result = installer.install(
                        url="https://github.com/user/repo.git",
                        path=".claude/skills/my-skill",
                    )

                    assert result.success is True

                    # Check metadata includes path
                    installed_skill = tmp_path / "my-skill"
                    assert installed_skill.exists()
                    metadata_file = installed_skill / INSTALLED_METADATA_FILE
                    assert metadata_file.exists()

                    metadata = json.loads(metadata_file.read_text())
                    assert metadata["path"] == ".claude/skills/my-skill"
                    assert metadata["source"] == "https://github.com/user/repo.git"

    def test_install_with_path_not_found(self, tmp_path: Path) -> None:
        """Test install with --path when path doesn't exist."""
        installer = SkillInstaller(skills_dir=tmp_path)

        with patch.object(installer, "_clone_with_sparse_checkout") as mock_sparse:
            with patch.object(installer, "_get_current_commit", return_value="abc123"):
                with patch("tempfile.TemporaryDirectory") as mock_tmpdir:
                    mock_tmp = tmp_path / "mock_tmp"
                    mock_tmp.mkdir()
                    mock_repo = mock_tmp / "repo"
                    mock_repo.mkdir()

                    mock_tmpdir.return_value.__enter__.return_value = str(mock_tmp)
                    mock_sparse.return_value = None

                    result = installer.install(
                        url="https://github.com/user/repo.git",
                        path="nonexistent/path",
                    )

                    assert result.success is False
                    assert "not found" in result.message

    def test_install_with_path_no_skill(self, tmp_path: Path) -> None:
        """Test install with --path when path exists but has no SKILL.md."""
        installer = SkillInstaller(skills_dir=tmp_path)

        with patch.object(installer, "_clone_with_sparse_checkout") as mock_sparse:
            with patch.object(installer, "_get_current_commit", return_value="abc123"):
                with patch("tempfile.TemporaryDirectory") as mock_tmpdir:
                    mock_tmp = tmp_path / "mock_tmp"
                    mock_tmp.mkdir()
                    mock_repo = mock_tmp / "repo"
                    mock_repo.mkdir()

                    # Create path without SKILL.md
                    empty_path = mock_repo / "some" / "path"
                    empty_path.mkdir(parents=True)
                    (empty_path / "README.md").write_text("# Not a skill")

                    mock_tmpdir.return_value.__enter__.return_value = str(mock_tmp)
                    mock_sparse.return_value = None

                    result = installer.install(
                        url="https://github.com/user/repo.git",
                        path="some/path",
                    )

                    assert result.success is False
                    assert "No skills found" in result.message


class TestFindSkillsInRepo:
    """Tests for finding skills in repository."""

    def test_single_skill_repo(self, tmp_path: Path) -> None:
        """Test finding skill in single-skill repo."""
        installer = SkillInstaller(skills_dir=tmp_path)

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / SKILL_FILE_NAME).write_text("---\nname: my-skill\n---\n")

        skills = installer._find_skills_in_repo(repo_dir)

        assert len(skills) == 1
        assert skills[0] == repo_dir

    def test_multi_skill_repo(self, tmp_path: Path) -> None:
        """Test finding skills in multi-skill repo."""
        installer = SkillInstaller(skills_dir=tmp_path)

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        # Create multiple skill directories
        skill1 = repo_dir / "skill-a"
        skill1.mkdir()
        (skill1 / SKILL_FILE_NAME).write_text("---\nname: skill-a\n---\n")

        skill2 = repo_dir / "skill-b"
        skill2.mkdir()
        (skill2 / SKILL_FILE_NAME).write_text("---\nname: skill-b\n---\n")

        # Create a non-skill directory
        (repo_dir / "docs").mkdir()
        (repo_dir / "README.md").write_text("# Readme")

        skills = installer._find_skills_in_repo(repo_dir)

        assert len(skills) == 2
        skill_names = {s.name for s in skills}
        assert skill_names == {"skill-a", "skill-b"}

    def test_no_skills_in_repo(self, tmp_path: Path) -> None:
        """Test empty repo with no skills."""
        installer = SkillInstaller(skills_dir=tmp_path)

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "README.md").write_text("# Empty repo")

        skills = installer._find_skills_in_repo(repo_dir)

        assert skills == []

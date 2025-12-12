"""Skill installer module.

Provides functionality to install, uninstall, and list skills from Git repositories.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Default skills directory
DEFAULT_SKILLS_DIR = Path.home() / ".agent-skills" / "skills"

# Metadata file name for installed skills
INSTALLED_METADATA_FILE = ".installed.json"

# Skill definition file
SKILL_FILE_NAME = "SKILL.md"


@dataclass
class InstallResult:
    """Result of an install operation."""
    success: bool
    message: str
    skill_name: str | None = None
    skill_path: str | None = None


@dataclass
class SkillInfo:
    """Information about an installed skill."""
    name: str
    path: str
    description: str = ""
    source: str | None = None
    ref: str | None = None
    installed_at: str | None = None
    is_installed: bool = False  # True if installed via CLI


class SkillInstaller:
    """Handles skill installation, uninstallation, and listing."""

    def __init__(self, skills_dir: Path | str | None = None):
        """
        Initialize the installer.

        Args:
            skills_dir: Directory to install skills to. Defaults to ~/.agent-skills/skills/
        """
        if skills_dir is None:
            self.skills_dir = DEFAULT_SKILLS_DIR
        else:
            self.skills_dir = Path(skills_dir).resolve()

    def _ensure_skills_dir(self) -> None:
        """Ensure the skills directory exists."""
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def _extract_repo_name(self, url: str) -> str:
        """
        Extract repository name from Git URL.

        Examples:
            https://github.com/user/my-skill.git -> my-skill
            git@github.com:user/my-skill.git -> my-skill
            https://github.com/user/my-skill -> my-skill
        """
        # Remove .git suffix if present
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]

        # Extract the last path component
        name = url.split("/")[-1]

        # Handle SSH format (git@github.com:user/repo)
        if ":" in name and "@" in url:
            name = name.split(":")[-1].split("/")[-1]

        return name

    def _run_git_command(
        self,
        args: list[str],
        cwd: Path | str | None = None,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """
        Run a git command.

        Args:
            args: Git command arguments (without 'git' prefix)
            cwd: Working directory
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess result

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        cmd = ["git"] + args
        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=True,
        )

    def _get_current_commit(self, repo_path: Path) -> str:
        """Get the current commit hash of a repository."""
        result = self._run_git_command(
            ["rev-parse", "HEAD"],
            cwd=repo_path,
        )
        return result.stdout.strip()[:12]

    def _write_metadata(
        self,
        skill_path: Path,
        source: str,
        ref: str | None,
        commit: str,
        repo_path: str | None = None,
    ) -> None:
        """Write installation metadata to skill directory."""
        metadata = {
            "source": source,
            "ref": ref,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "commit": commit,
        }
        if repo_path:
            metadata["path"] = repo_path
        metadata_file = skill_path / INSTALLED_METADATA_FILE
        metadata_file.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _read_metadata(self, skill_path: Path) -> dict[str, Any] | None:
        """Read installation metadata from skill directory."""
        metadata_file = skill_path / INSTALLED_METADATA_FILE
        if not metadata_file.exists():
            return None
        try:
            return json.loads(metadata_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _parse_skill_file(self, skill_path: Path) -> dict[str, str]:
        """Parse SKILL.md frontmatter to extract name and description."""
        skill_file = skill_path / SKILL_FILE_NAME
        if not skill_file.exists():
            return {}

        try:
            content = skill_file.read_text(encoding="utf-8")
            # Match YAML frontmatter
            match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if not match:
                return {}

            # Simple YAML parsing for name and description
            frontmatter = match.group(1)
            result: dict[str, str] = {}

            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key in ("name", "description"):
                        result[key] = value

            return result
        except Exception:
            return {}

    def _is_single_skill_repo(self, repo_path: Path) -> bool:
        """Check if repository contains a single skill (SKILL.md at root)."""
        return (repo_path / SKILL_FILE_NAME).exists()

    def _find_skills_in_repo(self, repo_path: Path) -> list[Path]:
        """
        Find all skill directories in a repository.

        Returns:
            List of paths to skill directories (containing SKILL.md)
        """
        skills: list[Path] = []

        # Check if root is a skill
        if self._is_single_skill_repo(repo_path):
            return [repo_path]

        # Search subdirectories
        for item in repo_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                if (item / SKILL_FILE_NAME).exists():
                    skills.append(item)

        return skills

    def _clone_with_sparse_checkout(
        self,
        url: str,
        target_path: Path,
        sparse_path: str,
        ref: str | None = None,
    ) -> None:
        """
        Clone a repository with sparse checkout to only download specific directory.

        Args:
            url: Git repository URL
            target_path: Path to clone to
            sparse_path: Path within repository to checkout
            ref: Git ref (branch, tag, or commit) to checkout
        """
        # Initialize empty repo
        self._run_git_command(["init", str(target_path)])

        # Add remote
        self._run_git_command(["remote", "add", "origin", url], cwd=target_path)

        # Enable sparse checkout
        self._run_git_command(
            ["config", "core.sparseCheckout", "true"],
            cwd=target_path,
        )

        # Configure sparse checkout path
        sparse_checkout_file = target_path / ".git" / "info" / "sparse-checkout"
        sparse_checkout_file.parent.mkdir(parents=True, exist_ok=True)
        sparse_checkout_file.write_text(f"{sparse_path}\n", encoding="utf-8")

        # Fetch and checkout
        fetch_args = ["fetch", "--depth", "1", "origin"]
        if ref:
            fetch_args.append(ref)
        else:
            fetch_args.append("HEAD")

        self._run_git_command(fetch_args, cwd=target_path)

        # Checkout
        checkout_ref = ref if ref else "FETCH_HEAD"
        self._run_git_command(["checkout", checkout_ref], cwd=target_path)

    def install(
        self,
        url: str,
        ref: str | None = None,
        name: str | None = None,
        path: str | None = None,
    ) -> InstallResult:
        """
        Install a skill from a Git repository.

        Args:
            url: Git repository URL
            ref: Git ref (branch, tag, or commit) to checkout
            name: Custom name for the skill (only for single-skill repos)
            path: Path within repository to install (for large repos with skills in subdirectories)

        Returns:
            InstallResult indicating success or failure
        """
        self._ensure_skills_dir()

        # Create temporary directory for cloning
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / "repo"

            try:
                if path:
                    # Use sparse checkout to only download the specified path
                    try:
                        self._clone_with_sparse_checkout(url, tmp_path, path, ref)
                    except subprocess.CalledProcessError as e:
                        error_msg = e.stderr if e.stderr else str(e)
                        return InstallResult(
                            success=False,
                            message=f"Failed to clone with sparse checkout: {error_msg}",
                        )

                    # Get commit hash
                    commit = self._get_current_commit(tmp_path)

                    # The skill should be at tmp_path / path
                    skill_source_path = tmp_path / path.strip("/")

                    if not skill_source_path.exists():
                        return InstallResult(
                            success=False,
                            message=f"Path '{path}' not found in repository.",
                        )

                    # Check if the path itself is a skill or contains skills
                    if (skill_source_path / SKILL_FILE_NAME).exists():
                        # The path is a skill directory
                        skill_dirs = [skill_source_path]
                    else:
                        # Search for skills within the path
                        skill_dirs = []
                        for item in skill_source_path.iterdir():
                            if item.is_dir() and not item.name.startswith("."):
                                if (item / SKILL_FILE_NAME).exists():
                                    skill_dirs.append(item)

                    if not skill_dirs:
                        return InstallResult(
                            success=False,
                            message=f"No skills found at path '{path}'. "
                            f"Expected {SKILL_FILE_NAME} in the directory or subdirectories.",
                        )

                else:
                    # Standard clone without sparse checkout
                    clone_args = ["clone", "--depth", "1"]
                    if ref:
                        clone_args.extend(["--branch", ref])
                    clone_args.extend([url, str(tmp_path)])

                    try:
                        self._run_git_command(clone_args)
                    except subprocess.CalledProcessError:
                        # If --branch failed (might be a commit hash), clone without it
                        if ref:
                            self._run_git_command(
                                ["clone", url, str(tmp_path)]
                            )
                            # Checkout the specific ref
                            self._run_git_command(
                                ["checkout", ref],
                                cwd=tmp_path,
                            )
                        else:
                            raise

                    # Get commit hash
                    commit = self._get_current_commit(tmp_path)

                    # Find skills in repository
                    skill_dirs = self._find_skills_in_repo(tmp_path)

                if not skill_dirs:
                    return InstallResult(
                        success=False,
                        message=f"No skills found in repository. "
                        f"Expected {SKILL_FILE_NAME} at root or in subdirectories.",
                    )

                installed_skills: list[str] = []

                for skill_dir in skill_dirs:
                    # Determine skill name
                    if len(skill_dirs) == 1 and name:
                        skill_name = name
                    elif skill_dir == tmp_path:
                        # Single skill at root, use repo name or custom name
                        skill_name = name or self._extract_repo_name(url)
                    else:
                        # Multi-skill repo, use directory name
                        skill_name = skill_dir.name

                    # Check if skill already exists
                    target_path = self.skills_dir / skill_name
                    if target_path.exists():
                        return InstallResult(
                            success=False,
                            message=f"Skill '{skill_name}' already exists at {target_path}. "
                            f"Use 'uninstall' first to remove it.",
                        )

                    # Remove .git directory before copying
                    git_dir = skill_dir / ".git" if skill_dir == tmp_path else tmp_path / ".git"
                    if skill_dir == tmp_path:
                        # Single skill repo - remove .git from the skill dir
                        shutil.rmtree(tmp_path / ".git", ignore_errors=True)

                    # Copy skill to target directory
                    if skill_dir == tmp_path:
                        # Single skill - copy entire repo (minus .git)
                        shutil.copytree(skill_dir, target_path)
                    else:
                        # Multi-skill - copy just the skill subdirectory
                        shutil.copytree(skill_dir, target_path)

                    # Write metadata
                    self._write_metadata(target_path, url, ref, commit, repo_path=path)

                    installed_skills.append(skill_name)

                if len(installed_skills) == 1:
                    return InstallResult(
                        success=True,
                        message=f"Successfully installed skill '{installed_skills[0]}'",
                        skill_name=installed_skills[0],
                        skill_path=str(self.skills_dir / installed_skills[0]),
                    )
                else:
                    names_str = ", ".join(installed_skills)
                    return InstallResult(
                        success=True,
                        message=f"Successfully installed {len(installed_skills)} skills: {names_str}",
                        skill_name=installed_skills[0],
                        skill_path=str(self.skills_dir),
                    )

            except subprocess.CalledProcessError as e:
                error_msg = e.stderr if e.stderr else str(e)
                return InstallResult(
                    success=False,
                    message=f"Git operation failed: {error_msg}",
                )
            except Exception as e:
                return InstallResult(
                    success=False,
                    message=f"Installation failed: {e}",
                )

    def uninstall(self, name: str) -> InstallResult:
        """
        Uninstall a skill.

        Args:
            name: Name of the skill to uninstall

        Returns:
            InstallResult indicating success or failure
        """
        skill_path = self.skills_dir / name

        if not skill_path.exists():
            return InstallResult(
                success=False,
                message=f"Skill '{name}' not found at {skill_path}",
            )

        # Check if it's a valid skill directory
        if not (skill_path / SKILL_FILE_NAME).exists():
            return InstallResult(
                success=False,
                message=f"'{name}' is not a valid skill (no {SKILL_FILE_NAME} found)",
            )

        try:
            shutil.rmtree(skill_path)
            return InstallResult(
                success=True,
                message=f"Successfully uninstalled skill '{name}'",
                skill_name=name,
            )
        except Exception as e:
            return InstallResult(
                success=False,
                message=f"Failed to uninstall skill '{name}': {e}",
            )

    def list_skills(self, installed_only: bool = False) -> list[SkillInfo]:
        """
        List all skills in the skills directory.

        Args:
            installed_only: If True, only show skills installed via CLI

        Returns:
            List of SkillInfo objects
        """
        if not self.skills_dir.exists():
            return []

        skills: list[SkillInfo] = []

        for item in sorted(self.skills_dir.iterdir()):
            if not item.is_dir() or item.name.startswith("."):
                continue

            skill_file = item / SKILL_FILE_NAME
            if not skill_file.exists():
                continue

            # Parse skill metadata
            parsed = self._parse_skill_file(item)
            metadata = self._read_metadata(item)

            is_installed = metadata is not None

            # Skip non-installed skills if installed_only
            if installed_only and not is_installed:
                continue

            skill_info = SkillInfo(
                name=parsed.get("name", item.name),
                path=str(item),
                description=parsed.get("description", ""),
                source=metadata.get("source") if metadata else None,
                ref=metadata.get("ref") if metadata else None,
                installed_at=metadata.get("installed_at") if metadata else None,
                is_installed=is_installed,
            )
            skills.append(skill_info)

        return skills

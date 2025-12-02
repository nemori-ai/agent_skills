"""Tests for Sandbox module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_skills.sandbox.sandbox import Sandbox, SandboxConfig


class TestSandboxPathResolution:
    """Tests for path resolution and security."""

    def test_resolve_relative_path(
        self, sandbox: Sandbox, temp_workspace: Path
    ) -> None:
        """Test resolving a relative path."""
        resolved = sandbox.resolve_path("subdir/file.txt")
        expected = (temp_workspace / "subdir" / "file.txt").resolve()
        assert resolved == expected

    def test_resolve_absolute_path_in_workspace(
        self, sandbox: Sandbox, temp_workspace: Path
    ) -> None:
        """Test resolving an absolute path within workspace."""
        abs_path = temp_workspace / "file.txt"
        resolved = sandbox.resolve_path(str(abs_path))
        assert resolved == abs_path.resolve()

    def test_reject_path_outside_workspace(
        self, sandbox: Sandbox, temp_workspace: Path
    ) -> None:
        """Test that paths outside workspace are rejected."""
        with pytest.raises(PermissionError) as exc_info:
            sandbox.resolve_path("/etc/passwd")
        assert "outside workspace" in str(exc_info.value)

    def test_reject_path_traversal(
        self, sandbox: Sandbox, temp_workspace: Path
    ) -> None:
        """Test that path traversal attempts are rejected."""
        with pytest.raises(PermissionError):
            sandbox.resolve_path("../../../etc/passwd")


class TestSandboxBlacklist:
    """Tests for blacklist functionality."""

    def test_reject_git_directory(
        self, sandbox: Sandbox, temp_workspace: Path
    ) -> None:
        """Test that .git directory is blacklisted."""
        git_dir = temp_workspace / ".git"
        git_dir.mkdir()

        with pytest.raises(PermissionError) as exc_info:
            sandbox.resolve_path(".git/config")
        assert "blacklist" in str(exc_info.value)

    def test_reject_env_file(
        self, sandbox: Sandbox, temp_workspace: Path
    ) -> None:
        """Test that .env files are blacklisted."""
        env_file = temp_workspace / ".env"
        env_file.write_text("SECRET=value")

        with pytest.raises(PermissionError):
            sandbox.resolve_path(".env")

    def test_custom_blacklist(self, temp_workspace: Path) -> None:
        """Test custom blacklist patterns."""
        config = SandboxConfig(
            workspace_root=str(temp_workspace),
            blacklist=["*.secret", "private/*"],
        )
        sandbox = Sandbox(config)

        with pytest.raises(PermissionError):
            sandbox.resolve_path("config.secret")


class TestSandboxWriteControl:
    """Tests for write access control."""

    def test_write_allowed_by_default(self, sandbox: Sandbox) -> None:
        """Test that write is allowed by default."""
        sandbox.check_write_allowed()  # Should not raise

    def test_write_denied_in_readonly_mode(self, temp_workspace: Path) -> None:
        """Test that write is denied in readonly mode."""
        config = SandboxConfig(
            workspace_root=str(temp_workspace),
            allow_write=False,
        )
        sandbox = Sandbox(config)

        with pytest.raises(PermissionError) as exc_info:
            sandbox.check_write_allowed()
        assert "Write operations are not allowed" in str(exc_info.value)


class TestSandboxFileSizeLimit:
    """Tests for file size limits."""

    def test_file_size_within_limit(self, sandbox: Sandbox) -> None:
        """Test that files within size limit are allowed."""
        sandbox.check_file_size(1024)  # 1 KB

    def test_file_size_exceeds_limit(self, temp_workspace: Path) -> None:
        """Test that files exceeding size limit are rejected."""
        config = SandboxConfig(
            workspace_root=str(temp_workspace),
            max_file_size=1024,  # 1 KB
        )
        sandbox = Sandbox(config)

        with pytest.raises(ValueError) as exc_info:
            sandbox.check_file_size(2048)  # 2 KB
        assert "exceeds maximum" in str(exc_info.value)


class TestSandboxCommandValidation:
    """Tests for command validation."""

    def test_allow_safe_command(self, sandbox: Sandbox) -> None:
        """Test that safe commands are allowed."""
        sandbox.validate_command("echo 'hello'")
        sandbox.validate_command("ls -la")
        sandbox.validate_command("cat file.txt")

    def test_reject_dangerous_rm(self, sandbox: Sandbox) -> None:
        """Test that dangerous rm commands are blocked."""
        with pytest.raises(PermissionError):
            sandbox.validate_command("rm -rf /")

    def test_reject_fork_bomb(self, sandbox: Sandbox) -> None:
        """Test that fork bombs are blocked."""
        # The exact fork bomb pattern in blacklist
        with pytest.raises(PermissionError):
            sandbox.validate_command(":(){:|:&};:")


class TestSandboxEnvironment:
    """Tests for safe environment generation."""

    def test_safe_env_has_path(self, sandbox: Sandbox) -> None:
        """Test that safe env includes PATH."""
        env = sandbox.get_safe_env()
        assert "PATH" in env
        assert "/usr/bin" in env["PATH"]

    def test_safe_env_sets_home(self, sandbox: Sandbox) -> None:
        """Test that safe env sets HOME to workspace."""
        env = sandbox.get_safe_env()
        assert "HOME" in env
        assert env["HOME"] == str(sandbox.workspace_root)


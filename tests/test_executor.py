"""Tests for Executor module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_skills.core.executor import Executor
from agent_skills.core.types import BackgroundTask, ToolStatus


class TestBash:
    """Tests for the bash command."""

    @pytest.mark.asyncio
    async def test_bash_simple_command(self, executor: Executor) -> None:
        """Test executing a simple command."""
        result = await executor.bash("echo 'Hello, World!'")
        assert result.status == ToolStatus.SUCCESS
        assert "Hello, World!" in result.stdout

    @pytest.mark.asyncio
    async def test_bash_exit_code(self, executor: Executor) -> None:
        """Test command exit code handling."""
        result = await executor.bash("exit 0")
        assert result.exit_code == 0

        result = await executor.bash("exit 1")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_bash_stderr(self, executor: Executor) -> None:
        """Test capturing stderr."""
        result = await executor.bash("echo 'error' >&2")
        assert "error" in result.stderr

    @pytest.mark.asyncio
    async def test_bash_timeout(self, executor: Executor) -> None:
        """Test command timeout."""
        result = await executor.bash("sleep 10", timeout=1)
        assert result.timed_out is True
        assert result.exit_code == 124

    @pytest.mark.asyncio
    async def test_bash_cwd(
        self, executor: Executor, temp_workspace: Path
    ) -> None:
        """Test command with custom working directory."""
        subdir = temp_workspace / "subdir"
        subdir.mkdir()

        result = await executor.bash("pwd", cwd=str(subdir))
        assert result.status == ToolStatus.SUCCESS
        assert "subdir" in result.stdout

    @pytest.mark.asyncio
    async def test_bash_combined_commands(self, executor: Executor) -> None:
        """Test running multiple commands."""
        result = await executor.bash("echo 'line1' && echo 'line2'")
        assert result.status == ToolStatus.SUCCESS
        assert "line1" in result.stdout
        assert "line2" in result.stdout


class TestBg:
    """Tests for the bg (background) command."""

    @pytest.mark.asyncio
    async def test_bg_start_process(self, executor: Executor) -> None:
        """Test starting a background process."""
        result = await executor.bg("sleep 60")
        assert isinstance(result, BackgroundTask)
        assert result.pid > 0

        # Clean up
        executor.kill(result.pid)

    @pytest.mark.asyncio
    async def test_bg_returns_pid(self, executor: Executor) -> None:
        """Test that bg returns process ID."""
        result = await executor.bg("sleep 60")
        assert isinstance(result, BackgroundTask)
        assert result.command == "sleep 60"

        # Clean up
        executor.kill(result.pid)


class TestJobs:
    """Tests for the jobs command."""

    @pytest.mark.asyncio
    async def test_jobs_empty(self, executor: Executor) -> None:
        """Test jobs when no background tasks."""
        jobs = executor.jobs()
        assert jobs == []

    @pytest.mark.asyncio
    async def test_jobs_lists_tasks(self, executor: Executor) -> None:
        """Test that jobs lists background tasks."""
        result = await executor.bg("sleep 60")
        assert isinstance(result, BackgroundTask)

        jobs = executor.jobs()
        assert len(jobs) >= 1
        assert any(j.pid == result.pid for j in jobs)

        # Clean up
        executor.kill(result.pid)


class TestKill:
    """Tests for the kill command."""

    @pytest.mark.asyncio
    async def test_kill_process(self, executor: Executor) -> None:
        """Test killing a background process."""
        result = await executor.bg("sleep 60")
        assert isinstance(result, BackgroundTask)

        kill_result = executor.kill(result.pid)
        assert kill_result.status == ToolStatus.SUCCESS

    def test_kill_nonexistent(self, executor: Executor) -> None:
        """Test killing a nonexistent process."""
        result = executor.kill(999999)
        assert result.status == ToolStatus.ERROR


class TestBashSync:
    """Tests for the synchronous bash wrapper."""

    def test_bash_sync(self, executor: Executor) -> None:
        """Test synchronous bash execution."""
        result = executor.bash_sync("echo 'sync test'")
        assert result.status == ToolStatus.SUCCESS
        assert "sync test" in result.stdout


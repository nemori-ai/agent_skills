"""Executor module for command execution.

Provides: bash, bg
"""

from __future__ import annotations

import asyncio
import os
import signal
import time
from datetime import datetime
from typing import TYPE_CHECKING

from agent_skills.core.types import BackgroundTask, CommandResult, ToolStatus

if TYPE_CHECKING:
    from agent_skills.sandbox.sandbox import Sandbox


class Executor:
    """Command execution with sandbox security and timeout control."""

    def __init__(self, sandbox: Sandbox) -> None:
        """
        Initialize Executor with a sandbox.

        Args:
            sandbox: Security sandbox for command validation
        """
        self.sandbox = sandbox
        self._background_tasks: dict[int, BackgroundTask] = {}

    async def bash(
        self,
        command: str,
        timeout: int = 30,
        cwd: str | None = None,
    ) -> CommandResult:
        """
        Execute a shell command (like bash -c).

        Args:
            command: The shell command to execute
            timeout: Maximum execution time in seconds
            cwd: Working directory (defaults to workspace root)

        Returns:
            CommandResult with stdout, stderr, and exit code
        """
        start_time = time.time()

        try:
            # Validate command
            self.sandbox.validate_command(command)

            # Resolve working directory
            if cwd:
                work_dir = str(self.sandbox.resolve_path(cwd))
            else:
                work_dir = str(self.sandbox.workspace_root)

            # Get safe environment
            env = self.sandbox.get_safe_env()
            env["PWD"] = work_dir

            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env=env,
            )

            try:
                # Wait with timeout
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )

                duration_ms = int((time.time() - start_time) * 1000)

                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")

                exit_code = process.returncode or 0

                if exit_code == 0:
                    return CommandResult.success(
                        stdout=stdout,
                        stderr=stderr,
                        command=command,
                        exit_code=exit_code,
                        duration_ms=duration_ms,
                    )
                else:
                    return CommandResult(
                        status=ToolStatus.ERROR,
                        exit_code=exit_code,
                        stdout=stdout,
                        stderr=stderr,
                        command=command,
                        duration_ms=duration_ms,
                    )

            except asyncio.TimeoutError:
                # Kill the process
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass

                duration_ms = int((time.time() - start_time) * 1000)

                return CommandResult.error(
                    stderr=f"Command timed out after {timeout} seconds",
                    command=command,
                    exit_code=124,  # Standard timeout exit code
                    timed_out=True,
                )

        except PermissionError as e:
            return CommandResult.error(
                stderr=f"Permission denied: {e}",
                command=command,
            )
        except Exception as e:
            return CommandResult.error(
                stderr=f"Execution error: {e}",
                command=command,
            )

    def bash_sync(
        self,
        command: str,
        timeout: int = 30,
        cwd: str | None = None,
    ) -> CommandResult:
        """
        Synchronous wrapper for bash command execution.

        Args:
            command: The shell command to execute
            timeout: Maximum execution time in seconds
            cwd: Working directory (defaults to workspace root)

        Returns:
            CommandResult with stdout, stderr, and exit code
        """
        return asyncio.get_event_loop().run_until_complete(
            self.bash(command, timeout, cwd)
        )

    async def bg(
        self,
        command: str,
        cwd: str | None = None,
    ) -> BackgroundTask | CommandResult:
        """
        Execute a command in the background.

        The command runs asynchronously and its PID is returned.
        Use the jobs() method to check running background tasks.

        Args:
            command: The shell command to execute
            cwd: Working directory (defaults to workspace root)

        Returns:
            BackgroundTask with PID or CommandResult if failed to start
        """
        try:
            # Validate command
            self.sandbox.validate_command(command)

            # Resolve working directory
            if cwd:
                work_dir = str(self.sandbox.resolve_path(cwd))
            else:
                work_dir = str(self.sandbox.workspace_root)

            # Get safe environment
            env = self.sandbox.get_safe_env()
            env["PWD"] = work_dir

            # Create subprocess (don't capture output for background tasks)
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                cwd=work_dir,
                env=env,
                start_new_session=True,  # Detach from parent
            )

            task = BackgroundTask(
                pid=process.pid,
                command=command,
                started_at=datetime.now(),
                cwd=work_dir,
            )

            # Track the task
            self._background_tasks[process.pid] = task

            return task

        except PermissionError as e:
            return CommandResult.error(
                stderr=f"Permission denied: {e}",
                command=command,
            )
        except Exception as e:
            return CommandResult.error(
                stderr=f"Failed to start background task: {e}",
                command=command,
            )

    def jobs(self) -> list[BackgroundTask]:
        """
        List running background tasks.

        Returns:
            List of BackgroundTask objects
        """
        # Clean up completed tasks
        completed_pids: list[int] = []
        for pid in self._background_tasks:
            try:
                # Check if process is still running
                os.kill(pid, 0)
            except OSError:
                completed_pids.append(pid)

        for pid in completed_pids:
            del self._background_tasks[pid]

        return list(self._background_tasks.values())

    def kill(self, pid: int, signal_num: int = signal.SIGTERM) -> CommandResult:
        """
        Send a signal to a process.

        Args:
            pid: Process ID to signal
            signal_num: Signal number (default: SIGTERM)

        Returns:
            CommandResult indicating success or failure
        """
        try:
            os.kill(pid, signal_num)

            # Remove from tracked tasks if present
            if pid in self._background_tasks:
                del self._background_tasks[pid]

            return CommandResult.success(
                stdout=f"Sent signal {signal_num} to process {pid}",
                command=f"kill -{signal_num} {pid}",
            )
        except ProcessLookupError:
            return CommandResult.error(
                stderr=f"No such process: {pid}",
                command=f"kill -{signal_num} {pid}",
            )
        except PermissionError:
            return CommandResult.error(
                stderr=f"Permission denied: cannot send signal to {pid}",
                command=f"kill -{signal_num} {pid}",
            )
        except Exception as e:
            return CommandResult.error(
                stderr=f"Error sending signal: {e}",
                command=f"kill -{signal_num} {pid}",
            )


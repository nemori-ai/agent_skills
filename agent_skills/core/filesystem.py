"""FileSystem module with Unix-style commands.

Provides: cat, ls, find, grep, touch, mkdir, rm, cp, mv
"""

from __future__ import annotations

import fnmatch
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from agent_skills.core.types import FileInfo, ToolResult, ToolStatus

if TYPE_CHECKING:
    from agent_skills.sandbox.sandbox import Sandbox


class FileSystem:
    """Unix-style file system operations with sandbox security."""

    def __init__(self, sandbox: Sandbox) -> None:
        """
        Initialize FileSystem with a sandbox.

        Args:
            sandbox: Security sandbox for path validation
        """
        self.sandbox = sandbox

    def cat(
        self,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        number: bool = False,
    ) -> ToolResult:
        """
        Read file contents (like Unix cat command).

        Args:
            path: Path to the file to read
            start_line: Start reading from this line (1-indexed, inclusive)
            end_line: Stop reading at this line (1-indexed, inclusive)
            number: If True, prepend line numbers to output

        Returns:
            ToolResult with file contents or error message
        """
        try:
            resolved = self.sandbox.resolve_path(path)

            if not resolved.exists():
                return ToolResult.error(f"cat: {path}: No such file or directory")

            if resolved.is_dir():
                return ToolResult.error(f"cat: {path}: Is a directory")

            # Check file size
            file_size = resolved.stat().st_size
            self.sandbox.check_file_size(file_size)

            # Read file
            content = resolved.read_text(encoding="utf-8")
            lines = content.splitlines(keepends=True)

            # Apply line range if specified
            if start_line is not None or end_line is not None:
                start_idx = (start_line - 1) if start_line else 0
                end_idx = end_line if end_line else len(lines)
                start_idx = max(0, start_idx)
                end_idx = min(len(lines), end_idx)
                lines = lines[start_idx:end_idx]

                # Adjust line numbering offset
                line_offset = start_idx
            else:
                line_offset = 0

            # Add line numbers if requested
            if number:
                numbered_lines: list[str] = []
                for i, line in enumerate(lines):
                    line_num = i + line_offset + 1
                    # Right-align line numbers (6 chars)
                    numbered_lines.append(f"{line_num:6}| {line}")
                output = "".join(numbered_lines)
            else:
                output = "".join(lines)

            return ToolResult.success(data=output)

        except PermissionError as e:
            return ToolResult.error(f"cat: {path}: {e}")
        except UnicodeDecodeError:
            return ToolResult.error(f"cat: {path}: Binary file (not text)")
        except Exception as e:
            return ToolResult.error(f"cat: {path}: {e}")

    def ls(
        self,
        path: str = ".",
        all: bool = False,
        long: bool = False,
        recursive: bool = False,
    ) -> ToolResult:
        """
        List directory contents (like Unix ls command).

        Args:
            path: Directory path to list
            all: Include hidden files (starting with .)
            long: Use long listing format with details
            recursive: List subdirectories recursively

        Returns:
            ToolResult with directory listing
        """
        try:
            resolved = self.sandbox.resolve_path(path)

            if not resolved.exists():
                return ToolResult.error(f"ls: {path}: No such file or directory")

            if resolved.is_file():
                # If it's a file, just show the file info
                info = self._get_file_info(resolved)
                output = self._format_file_info(info, long)
                return ToolResult.success(data=output)

            # List directory
            entries: list[FileInfo] = []
            for item in sorted(resolved.iterdir()):
                # Skip hidden files unless -a flag
                if not all and item.name.startswith("."):
                    continue

                # Check if accessible
                try:
                    self.sandbox.resolve_path(str(item))
                except PermissionError:
                    continue

                info = self._get_file_info(item)
                entries.append(info)

            # Format output
            if long:
                lines: list[str] = [self._format_file_info(e, long=True) for e in entries]
                output = "\n".join(lines)
            else:
                names: list[str] = []
                for e in entries:
                    name = f"{e.name}/" if e.is_dir else e.name
                    names.append(name)
                output = "  ".join(names)

            # Handle recursive listing
            if recursive:
                for entry in entries:
                    if entry.is_dir:
                        subpath = str(Path(path) / entry.name)
                        sub_result = self.ls(subpath, all=all, long=long, recursive=True)
                        if sub_result.status == ToolStatus.SUCCESS and sub_result.data:
                            output += f"\n\n{subpath}:\n{sub_result.data}"

            return ToolResult.success(data=output)

        except PermissionError as e:
            return ToolResult.error(f"ls: {path}: {e}")
        except Exception as e:
            return ToolResult.error(f"ls: {path}: {e}")

    def find(
        self,
        path: str = ".",
        name: str | None = None,
        type: str | None = None,
        maxdepth: int | None = None,
    ) -> ToolResult:
        """
        Search for files in a directory hierarchy (like Unix find command).

        Args:
            path: Starting directory
            name: Pattern to match file names (glob pattern)
            type: Filter by type: 'f' for files, 'd' for directories
            maxdepth: Maximum depth to search

        Returns:
            ToolResult with matching file paths
        """
        try:
            resolved = self.sandbox.resolve_path(path)

            if not resolved.exists():
                return ToolResult.error(f"find: {path}: No such file or directory")

            matches: list[str] = []

            def search(current: Path, depth: int = 0) -> None:
                if maxdepth is not None and depth > maxdepth:
                    return

                try:
                    # Check if accessible
                    self.sandbox.resolve_path(str(current))
                except PermissionError:
                    return

                # Check if matches criteria
                matches_name = name is None or fnmatch.fnmatch(current.name, name)
                matches_type = True
                if type == "f":
                    matches_type = current.is_file()
                elif type == "d":
                    matches_type = current.is_dir()

                if matches_name and matches_type:
                    # Get relative path from search root
                    try:
                        rel_path = current.relative_to(resolved)
                        matches.append(str(Path(path) / rel_path))
                    except ValueError:
                        matches.append(str(current))

                # Recurse into directories
                if current.is_dir():
                    try:
                        for child in sorted(current.iterdir()):
                            search(child, depth + 1)
                    except PermissionError:
                        pass

            search(resolved)

            output = "\n".join(matches) if matches else ""
            return ToolResult.success(
                message=f"Found {len(matches)} item(s)",
                data=output,
            )

        except PermissionError as e:
            return ToolResult.error(f"find: {path}: {e}")
        except Exception as e:
            return ToolResult.error(f"find: {path}: {e}")

    def grep(
        self,
        pattern: str,
        path: str,
        recursive: bool = False,
        ignore_case: bool = False,
        line_number: bool = True,
        context: int = 0,
    ) -> ToolResult:
        """
        Search file contents for a pattern (like Unix grep command).

        Args:
            pattern: Regular expression pattern to search for
            path: File or directory to search
            recursive: Search directories recursively
            ignore_case: Case-insensitive matching
            line_number: Show line numbers
            context: Number of context lines before and after matches

        Returns:
            ToolResult with matching lines
        """
        try:
            resolved = self.sandbox.resolve_path(path)

            if not resolved.exists():
                return ToolResult.error(f"grep: {path}: No such file or directory")

            # Compile regex
            flags = re.IGNORECASE if ignore_case else 0
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return ToolResult.error(f"grep: Invalid pattern: {e}")

            results: list[str] = []

            def search_file(file_path: Path, display_path: str) -> list[str]:
                file_matches: list[str] = []
                try:
                    content = file_path.read_text(encoding="utf-8")
                    lines = content.splitlines()

                    matched_indices: set[int] = set()
                    for i, line in enumerate(lines):
                        if regex.search(line):
                            matched_indices.add(i)
                            # Add context lines
                            for j in range(max(0, i - context), min(len(lines), i + context + 1)):
                                matched_indices.add(j)

                    for i in sorted(matched_indices):
                        line = lines[i]
                        is_match = regex.search(line) is not None
                        prefix = ":" if is_match else "-"

                        if line_number:
                            file_matches.append(f"{display_path}{prefix}{i + 1}{prefix}{line}")
                        else:
                            file_matches.append(f"{display_path}{prefix}{line}")

                except (UnicodeDecodeError, PermissionError):
                    pass

                return file_matches

            if resolved.is_file():
                results.extend(search_file(resolved, path))
            elif resolved.is_dir():
                if recursive:
                    for root, dirs, files in os.walk(resolved):
                        # Filter out blacklisted directories
                        dirs[:] = [
                            d for d in dirs
                            if not d.startswith(".")
                            and self._is_path_allowed(Path(root) / d)
                        ]

                        for file in files:
                            file_path = Path(root) / file
                            if self._is_path_allowed(file_path):
                                rel_path = file_path.relative_to(resolved)
                                display_path = str(Path(path) / rel_path)
                                results.extend(search_file(file_path, display_path))
                else:
                    return ToolResult.error(f"grep: {path}: Is a directory")

            output = "\n".join(results)
            return ToolResult.success(
                message=f"Found {len([r for r in results if ':' in r])} match(es)",
                data=output,
            )

        except PermissionError as e:
            return ToolResult.error(f"grep: {path}: {e}")
        except Exception as e:
            return ToolResult.error(f"grep: {path}: {e}")

    def touch(self, path: str) -> ToolResult:
        """
        Create an empty file or update timestamps (like Unix touch command).

        Args:
            path: Path to the file

        Returns:
            ToolResult indicating success or failure
        """
        try:
            self.sandbox.check_write_allowed()
            resolved = self.sandbox.resolve_path(path)

            # Create parent directories if needed
            resolved.parent.mkdir(parents=True, exist_ok=True)

            # Touch the file
            resolved.touch()

            return ToolResult.success(message=f"touch: created/updated '{path}'")

        except PermissionError as e:
            return ToolResult.error(f"touch: {path}: {e}")
        except Exception as e:
            return ToolResult.error(f"touch: {path}: {e}")

    def mkdir(self, path: str, parents: bool = False) -> ToolResult:
        """
        Create directories (like Unix mkdir command).

        Args:
            path: Path to the directory to create
            parents: Create parent directories as needed (like -p flag)

        Returns:
            ToolResult indicating success or failure
        """
        try:
            self.sandbox.check_write_allowed()
            resolved = self.sandbox.resolve_path(path)

            if resolved.exists():
                return ToolResult.error(f"mkdir: {path}: File exists")

            resolved.mkdir(parents=parents, exist_ok=False)
            return ToolResult.success(message=f"mkdir: created directory '{path}'")

        except FileNotFoundError:
            return ToolResult.error(
                f"mkdir: {path}: No such file or directory (use parents=True to create parent dirs)"
            )
        except PermissionError as e:
            return ToolResult.error(f"mkdir: {path}: {e}")
        except Exception as e:
            return ToolResult.error(f"mkdir: {path}: {e}")

    def rm(self, path: str, recursive: bool = False, force: bool = False) -> ToolResult:
        """
        Remove files or directories (like Unix rm command).

        Args:
            path: Path to remove
            recursive: Remove directories and their contents recursively
            force: Ignore nonexistent files and arguments

        Returns:
            ToolResult indicating success or failure
        """
        try:
            self.sandbox.check_write_allowed()
            resolved = self.sandbox.resolve_path(path)

            if not resolved.exists():
                if force:
                    return ToolResult.success(message=f"rm: '{path}' does not exist (ignored)")
                return ToolResult.error(f"rm: {path}: No such file or directory")

            if resolved.is_dir():
                if not recursive:
                    return ToolResult.error(f"rm: {path}: Is a directory (use recursive=True)")
                shutil.rmtree(resolved)
            else:
                resolved.unlink()

            return ToolResult.success(message=f"rm: removed '{path}'")

        except PermissionError as e:
            return ToolResult.error(f"rm: {path}: {e}")
        except Exception as e:
            return ToolResult.error(f"rm: {path}: {e}")

    def cp(self, src: str, dst: str, recursive: bool = False) -> ToolResult:
        """
        Copy files or directories (like Unix cp command).

        Args:
            src: Source path
            dst: Destination path
            recursive: Copy directories recursively

        Returns:
            ToolResult indicating success or failure
        """
        try:
            self.sandbox.check_write_allowed()
            src_resolved = self.sandbox.resolve_path(src)
            dst_resolved = self.sandbox.resolve_path(dst)

            if not src_resolved.exists():
                return ToolResult.error(f"cp: {src}: No such file or directory")

            if src_resolved.is_dir():
                if not recursive:
                    return ToolResult.error(f"cp: {src}: Is a directory (use recursive=True)")
                shutil.copytree(src_resolved, dst_resolved)
            else:
                # If destination is a directory, copy into it
                if dst_resolved.is_dir():
                    dst_resolved = dst_resolved / src_resolved.name
                shutil.copy2(src_resolved, dst_resolved)

            return ToolResult.success(message=f"cp: '{src}' -> '{dst}'")

        except PermissionError as e:
            return ToolResult.error(f"cp: {e}")
        except Exception as e:
            return ToolResult.error(f"cp: {e}")

    def mv(self, src: str, dst: str) -> ToolResult:
        """
        Move or rename files/directories (like Unix mv command).

        Args:
            src: Source path
            dst: Destination path

        Returns:
            ToolResult indicating success or failure
        """
        try:
            self.sandbox.check_write_allowed()
            src_resolved = self.sandbox.resolve_path(src)
            dst_resolved = self.sandbox.resolve_path(dst)

            if not src_resolved.exists():
                return ToolResult.error(f"mv: {src}: No such file or directory")

            # If destination is a directory, move into it
            if dst_resolved.is_dir():
                dst_resolved = dst_resolved / src_resolved.name

            shutil.move(str(src_resolved), str(dst_resolved))

            return ToolResult.success(message=f"mv: '{src}' -> '{dst}'")

        except PermissionError as e:
            return ToolResult.error(f"mv: {e}")
        except Exception as e:
            return ToolResult.error(f"mv: {e}")

    def _get_file_info(self, path: Path) -> FileInfo:
        """Get file information for a path."""
        stat = path.stat()
        return FileInfo(
            name=path.name,
            path=str(path),
            is_dir=path.is_dir(),
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime),
            permissions=self._format_permissions(stat.st_mode),
        )

    def _format_permissions(self, mode: int) -> str:
        """Format file permissions as rwxrwxrwx string."""
        perms: list[str] = []
        for who in range(2, -1, -1):
            for what in [4, 2, 1]:
                if mode & (what << (who * 3)):
                    perms.append("rwx"[{4: 0, 2: 1, 1: 2}[what]])
                else:
                    perms.append("-")
        return "".join(perms)

    def _format_file_info(self, info: FileInfo, long: bool = False) -> str:
        """Format file info for display."""
        if long:
            type_char = "d" if info.is_dir else "-"
            perms = info.permissions or "rw-r--r--"
            modified = info.modified.strftime("%Y-%m-%d %H:%M") if info.modified else ""
            name = f"{info.name}/" if info.is_dir else info.name
            return f"{type_char}{perms}  {info.size:>10}  {modified}  {name}"
        else:
            return f"{info.name}/" if info.is_dir else info.name

    def _is_path_allowed(self, path: Path) -> bool:
        """Check if a path is allowed without raising exception."""
        try:
            self.sandbox.resolve_path(str(path))
            return True
        except PermissionError:
            return False

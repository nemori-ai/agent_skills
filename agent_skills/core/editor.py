"""Editor module with Unix-style commands.

Provides: sed, write, append
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from agent_skills.core.types import EditResult, ToolResult, ToolStatus

if TYPE_CHECKING:
    from agent_skills.sandbox.sandbox import Sandbox


class Editor:
    """Unix-style file editing operations with sandbox security."""

    def __init__(self, sandbox: Sandbox):
        """
        Initialize Editor with a sandbox.

        Args:
            sandbox: Security sandbox for path validation
        """
        self.sandbox = sandbox

    def sed(
        self,
        path: str,
        old: str,
        new: str,
        global_replace: bool = False,
        regex: bool = False,
        ignore_case: bool = False,
    ) -> EditResult:
        """
        Edit file with search/replace (like Unix sed command).

        This performs in-place editing similar to `sed -i 's/old/new/'`.

        Args:
            path: Path to the file to edit
            old: String or pattern to search for
            new: Replacement string
            global_replace: Replace all occurrences (like sed 's/old/new/g')
            regex: Treat 'old' as a regular expression
            ignore_case: Case-insensitive matching

        Returns:
            EditResult with replacement count and status
        """
        try:
            self.sandbox.check_write_allowed()
            resolved = self.sandbox.resolve_path(path)

            if not resolved.exists():
                return EditResult.error(f"sed: {path}: No such file or directory", path)

            if resolved.is_dir():
                return EditResult.error(f"sed: {path}: Is a directory", path)

            # Read current content
            content = resolved.read_text(encoding="utf-8")

            # Perform replacement
            if regex:
                flags = re.IGNORECASE if ignore_case else 0
                try:
                    pattern = re.compile(old, flags)
                except re.error as e:
                    return EditResult.error(f"sed: Invalid regex pattern: {e}", path)

                if global_replace:
                    new_content, count = pattern.subn(new, content)
                else:
                    new_content, count = pattern.subn(new, content, count=1)
            else:
                # Plain string replacement
                if ignore_case:
                    # Case-insensitive string replacement
                    pattern = re.compile(re.escape(old), re.IGNORECASE)
                    if global_replace:
                        new_content, count = pattern.subn(new, content)
                    else:
                        new_content, count = pattern.subn(new, content, count=1)
                else:
                    if global_replace:
                        count = content.count(old)
                        new_content = content.replace(old, new)
                    else:
                        count = 1 if old in content else 0
                        new_content = content.replace(old, new, 1)

            # Check if anything changed
            if count == 0:
                return EditResult(
                    status=ToolStatus.SUCCESS,
                    message=f"sed: no matches found for '{old}'",
                    path=path,
                    replacements=0,
                )

            # Write back
            resolved.write_text(new_content, encoding="utf-8")

            return EditResult.success(
                path=path,
                replacements=count,
                message=f"sed: replaced {count} occurrence(s) of '{old}'",
            )

        except PermissionError as e:
            return EditResult.error(f"sed: {path}: {e}", path)
        except UnicodeDecodeError:
            return EditResult.error(f"sed: {path}: Binary file (not text)", path)
        except Exception as e:
            return EditResult.error(f"sed: {path}: {e}", path)

    def write(self, path: str, content: str, create_dirs: bool = True) -> ToolResult:
        """
        Write content to a file (like echo > file).

        This overwrites the entire file content.

        Args:
            path: Path to the file to write
            content: Content to write
            create_dirs: Create parent directories if they don't exist

        Returns:
            ToolResult indicating success or failure
        """
        try:
            self.sandbox.check_write_allowed()
            resolved = self.sandbox.resolve_path(path)

            # Check content size
            self.sandbox.check_file_size(len(content.encode("utf-8")))

            if resolved.is_dir():
                return ToolResult.error(f"write: {path}: Is a directory")

            # Create parent directories if needed
            if create_dirs:
                resolved.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            resolved.write_text(content, encoding="utf-8")

            return ToolResult.success(
                message=f"write: wrote {len(content)} characters to '{path}'",
                data={"path": path, "size": len(content)},
            )

        except PermissionError as e:
            return ToolResult.error(f"write: {path}: {e}")
        except Exception as e:
            return ToolResult.error(f"write: {path}: {e}")

    def append(self, path: str, content: str, create: bool = True) -> ToolResult:
        """
        Append content to a file (like echo >> file).

        Args:
            path: Path to the file
            content: Content to append
            create: Create the file if it doesn't exist

        Returns:
            ToolResult indicating success or failure
        """
        try:
            self.sandbox.check_write_allowed()
            resolved = self.sandbox.resolve_path(path)

            if resolved.is_dir():
                return ToolResult.error(f"append: {path}: Is a directory")

            if not resolved.exists():
                if not create:
                    return ToolResult.error(f"append: {path}: No such file or directory")
                # Create parent directories
                resolved.parent.mkdir(parents=True, exist_ok=True)
                existing_content = ""
            else:
                existing_content = resolved.read_text(encoding="utf-8")

            # Check combined size
            new_content = existing_content + content
            self.sandbox.check_file_size(len(new_content.encode("utf-8")))

            # Write combined content
            resolved.write_text(new_content, encoding="utf-8")

            return ToolResult.success(
                message=f"append: appended {len(content)} characters to '{path}'",
                data={"path": path, "appended": len(content)},
            )

        except PermissionError as e:
            return ToolResult.error(f"append: {path}: {e}")
        except UnicodeDecodeError:
            return ToolResult.error(f"append: {path}: Binary file (not text)")
        except Exception as e:
            return ToolResult.error(f"append: {path}: {e}")

    def insert(
        self,
        path: str,
        content: str,
        line: int | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> ToolResult:
        """
        Insert content at a specific position in a file.

        Args:
            path: Path to the file
            content: Content to insert
            line: Insert at this line number (1-indexed)
            after: Insert after this string/pattern
            before: Insert before this string/pattern

        Returns:
            ToolResult indicating success or failure
        """
        try:
            self.sandbox.check_write_allowed()
            resolved = self.sandbox.resolve_path(path)

            if not resolved.exists():
                return ToolResult.error(f"insert: {path}: No such file or directory")

            if resolved.is_dir():
                return ToolResult.error(f"insert: {path}: Is a directory")

            # Read current content
            file_content = resolved.read_text(encoding="utf-8")
            lines = file_content.splitlines(keepends=True)

            if line is not None:
                # Insert at line number
                insert_idx = min(max(0, line - 1), len(lines))
                # Ensure content ends with newline if inserting in middle
                insert_content = content if content.endswith("\n") else content + "\n"
                lines.insert(insert_idx, insert_content)
                new_content = "".join(lines)
                position = f"line {line}"

            elif after is not None:
                # Insert after pattern
                idx = file_content.find(after)
                if idx == -1:
                    return ToolResult.error(f"insert: pattern '{after}' not found")
                insert_pos = idx + len(after)
                new_content = file_content[:insert_pos] + content + file_content[insert_pos:]
                position = f"after '{after}'"

            elif before is not None:
                # Insert before pattern
                idx = file_content.find(before)
                if idx == -1:
                    return ToolResult.error(f"insert: pattern '{before}' not found")
                new_content = file_content[:idx] + content + file_content[idx:]
                position = f"before '{before}'"

            else:
                return ToolResult.error(
                    "insert: must specify one of: line, after, or before"
                )

            # Check size
            self.sandbox.check_file_size(len(new_content.encode("utf-8")))

            # Write back
            resolved.write_text(new_content, encoding="utf-8")

            return ToolResult.success(
                message=f"insert: inserted {len(content)} characters at {position}",
                data={"path": path, "inserted": len(content), "position": position},
            )

        except PermissionError as e:
            return ToolResult.error(f"insert: {path}: {e}")
        except UnicodeDecodeError:
            return ToolResult.error(f"insert: {path}: Binary file (not text)")
        except Exception as e:
            return ToolResult.error(f"insert: {path}: {e}")


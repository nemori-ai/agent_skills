"""Tests for Editor module."""

from __future__ import annotations

from pathlib import Path


from agent_skills.core.editor import Editor
from agent_skills.core.types import ToolStatus


class TestSed:
    """Tests for the sed command."""

    def test_sed_single_replace(
        self, editor: Editor, temp_workspace: Path
    ) -> None:
        """Test replacing a single occurrence."""
        file_path = temp_workspace / "test.txt"
        file_path.write_text("foo bar foo baz")

        result = editor.sed(str(file_path), "foo", "qux")
        assert result.status == ToolStatus.SUCCESS
        assert result.replacements == 1

        content = file_path.read_text()
        assert content == "qux bar foo baz"

    def test_sed_global_replace(
        self, editor: Editor, temp_workspace: Path
    ) -> None:
        """Test replacing all occurrences."""
        file_path = temp_workspace / "test.txt"
        file_path.write_text("foo bar foo baz foo")

        result = editor.sed(str(file_path), "foo", "qux", global_replace=True)
        assert result.status == ToolStatus.SUCCESS
        assert result.replacements == 3

        content = file_path.read_text()
        assert "foo" not in content
        assert content.count("qux") == 3

    def test_sed_regex(self, editor: Editor, temp_workspace: Path) -> None:
        """Test regex replacement."""
        file_path = temp_workspace / "test.txt"
        file_path.write_text("version: v1.2.3")

        result = editor.sed(str(file_path), r"v\d+\.\d+\.\d+", "v2.0.0", regex=True)
        assert result.status == ToolStatus.SUCCESS

        content = file_path.read_text()
        assert "v2.0.0" in content

    def test_sed_case_insensitive(
        self, editor: Editor, temp_workspace: Path
    ) -> None:
        """Test case-insensitive replacement."""
        file_path = temp_workspace / "test.txt"
        file_path.write_text("Hello HELLO hello")

        result = editor.sed(
            str(file_path), "hello", "hi", global_replace=True, ignore_case=True
        )
        assert result.status == ToolStatus.SUCCESS
        assert result.replacements == 3

    def test_sed_no_match(self, editor: Editor, temp_workspace: Path) -> None:
        """Test when pattern not found."""
        file_path = temp_workspace / "test.txt"
        file_path.write_text("hello world")

        result = editor.sed(str(file_path), "xyz", "abc")
        assert result.status == ToolStatus.SUCCESS
        assert result.replacements == 0

    def test_sed_nonexistent_file(self, editor: Editor) -> None:
        """Test editing nonexistent file."""
        result = editor.sed("nonexistent.txt", "foo", "bar")
        assert result.status == ToolStatus.ERROR


class TestWrite:
    """Tests for the write command."""

    def test_write_new_file(self, editor: Editor, temp_workspace: Path) -> None:
        """Test writing to a new file."""
        file_path = temp_workspace / "new.txt"

        result = editor.write(str(file_path), "Hello, World!")
        assert result.status == ToolStatus.SUCCESS
        assert file_path.read_text() == "Hello, World!"

    def test_write_overwrite(self, editor: Editor, temp_workspace: Path) -> None:
        """Test overwriting an existing file."""
        file_path = temp_workspace / "existing.txt"
        file_path.write_text("old content")

        result = editor.write(str(file_path), "new content")
        assert result.status == ToolStatus.SUCCESS
        assert file_path.read_text() == "new content"

    def test_write_creates_parent_dirs(
        self, editor: Editor, temp_workspace: Path
    ) -> None:
        """Test that write creates parent directories."""
        file_path = temp_workspace / "a" / "b" / "c.txt"

        result = editor.write(str(file_path), "content")
        assert result.status == ToolStatus.SUCCESS
        assert file_path.read_text() == "content"


class TestAppend:
    """Tests for the append command."""

    def test_append_to_file(self, editor: Editor, temp_workspace: Path) -> None:
        """Test appending to a file."""
        file_path = temp_workspace / "test.txt"
        file_path.write_text("line 1\n")

        result = editor.append(str(file_path), "line 2\n")
        assert result.status == ToolStatus.SUCCESS
        assert file_path.read_text() == "line 1\nline 2\n"

    def test_append_creates_file(self, editor: Editor, temp_workspace: Path) -> None:
        """Test that append creates file if it doesn't exist."""
        file_path = temp_workspace / "new.txt"

        result = editor.append(str(file_path), "content")
        assert result.status == ToolStatus.SUCCESS
        assert file_path.read_text() == "content"

    def test_append_no_create(self, editor: Editor, temp_workspace: Path) -> None:
        """Test append without creating file."""
        file_path = temp_workspace / "nonexistent.txt"

        result = editor.append(str(file_path), "content", create=False)
        assert result.status == ToolStatus.ERROR


class TestInsert:
    """Tests for the insert command."""

    def test_insert_at_line(self, editor: Editor, temp_workspace: Path) -> None:
        """Test inserting at a specific line."""
        file_path = temp_workspace / "test.txt"
        file_path.write_text("line 1\nline 3\n")

        result = editor.insert(str(file_path), "line 2\n", line=2)
        assert result.status == ToolStatus.SUCCESS
        assert file_path.read_text() == "line 1\nline 2\nline 3\n"

    def test_insert_after_pattern(
        self, editor: Editor, temp_workspace: Path
    ) -> None:
        """Test inserting after a pattern."""
        file_path = temp_workspace / "test.txt"
        file_path.write_text("start\nend")

        result = editor.insert(str(file_path), " middle ", after="start")
        assert result.status == ToolStatus.SUCCESS
        assert "start middle" in file_path.read_text()

    def test_insert_before_pattern(
        self, editor: Editor, temp_workspace: Path
    ) -> None:
        """Test inserting before a pattern."""
        file_path = temp_workspace / "test.txt"
        file_path.write_text("start\nend")

        result = editor.insert(str(file_path), "prefix ", before="end")
        assert result.status == ToolStatus.SUCCESS
        assert "prefix end" in file_path.read_text()


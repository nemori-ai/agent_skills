"""Tests for FileSystem module."""

from __future__ import annotations

from pathlib import Path


from agent_skills.core.filesystem import FileSystem
from agent_skills.core.types import ToolStatus


class TestCat:
    """Tests for the cat command."""

    def test_cat_file(self, filesystem: FileSystem, sample_file: Path) -> None:
        """Test reading a file."""
        result = filesystem.cat(str(sample_file))
        assert result.status == ToolStatus.SUCCESS
        assert "line 1" in result.data
        assert "line 2" in result.data

    def test_cat_with_line_numbers(self, filesystem: FileSystem, sample_file: Path) -> None:
        """Test reading a file with line numbers."""
        result = filesystem.cat(str(sample_file), number=True)
        assert result.status == ToolStatus.SUCCESS
        assert "1|" in result.data or "1 |" in result.data

    def test_cat_line_range(self, filesystem: FileSystem, sample_file: Path) -> None:
        """Test reading a specific line range."""
        result = filesystem.cat(str(sample_file), start_line=2, end_line=3)
        assert result.status == ToolStatus.SUCCESS
        assert "line 2" in result.data
        assert "line 3" in result.data
        assert "line 1" not in result.data

    def test_cat_nonexistent_file(self, filesystem: FileSystem) -> None:
        """Test reading a file that doesn't exist."""
        result = filesystem.cat("nonexistent.txt")
        assert result.status == ToolStatus.ERROR
        assert "No such file" in result.message

    def test_cat_directory(self, filesystem: FileSystem, sample_dir: Path) -> None:
        """Test that cat fails on directories."""
        result = filesystem.cat(str(sample_dir / "subdir1"))
        assert result.status == ToolStatus.ERROR
        assert "Is a directory" in result.message


class TestLs:
    """Tests for the ls command."""

    def test_ls_directory(self, filesystem: FileSystem, sample_dir: Path) -> None:
        """Test listing a directory."""
        result = filesystem.ls(str(sample_dir))
        assert result.status == ToolStatus.SUCCESS
        assert "file1.txt" in result.data
        assert "subdir1" in result.data

    def test_ls_with_hidden(self, filesystem: FileSystem, sample_dir: Path) -> None:
        """Test listing with hidden files."""
        result = filesystem.ls(str(sample_dir), all=True)
        assert result.status == ToolStatus.SUCCESS
        assert ".hidden" in result.data

    def test_ls_without_hidden(self, filesystem: FileSystem, sample_dir: Path) -> None:
        """Test listing without hidden files."""
        result = filesystem.ls(str(sample_dir), all=False)
        assert result.status == ToolStatus.SUCCESS
        assert ".hidden" not in result.data

    def test_ls_long_format(self, filesystem: FileSystem, sample_dir: Path) -> None:
        """Test listing in long format."""
        result = filesystem.ls(str(sample_dir), long=True)
        assert result.status == ToolStatus.SUCCESS
        # Long format should include permissions or size
        assert "file1.txt" in result.data

    def test_ls_nonexistent(self, filesystem: FileSystem) -> None:
        """Test listing a nonexistent directory."""
        result = filesystem.ls("nonexistent")
        assert result.status == ToolStatus.ERROR
        assert "No such file" in result.message


class TestFind:
    """Tests for the find command."""

    def test_find_by_name(self, filesystem: FileSystem, sample_dir: Path) -> None:
        """Test finding files by name pattern."""
        result = filesystem.find(str(sample_dir), name="*.txt")
        assert result.status == ToolStatus.SUCCESS
        assert "file1.txt" in result.data
        assert "file3.txt" in result.data

    def test_find_directories_only(self, filesystem: FileSystem, sample_dir: Path) -> None:
        """Test finding directories only."""
        result = filesystem.find(str(sample_dir), type="d")
        assert result.status == ToolStatus.SUCCESS
        assert "subdir1" in result.data
        assert "file1.txt" not in result.data

    def test_find_files_only(self, filesystem: FileSystem, sample_dir: Path) -> None:
        """Test finding files only."""
        result = filesystem.find(str(sample_dir), type="f", name="*.py")
        assert result.status == ToolStatus.SUCCESS
        assert "file2.py" in result.data

    def test_find_with_maxdepth(self, filesystem: FileSystem, sample_dir: Path) -> None:
        """Test finding with depth limit."""
        result = filesystem.find(str(sample_dir), name="*.txt", maxdepth=1)
        assert result.status == ToolStatus.SUCCESS
        assert "file1.txt" in result.data
        # Nested files should not be found
        assert "file4.txt" not in result.data


class TestGrep:
    """Tests for the grep command."""

    def test_grep_pattern(self, filesystem: FileSystem, sample_file: Path) -> None:
        """Test searching for a pattern."""
        result = filesystem.grep("foo", str(sample_file))
        assert result.status == ToolStatus.SUCCESS
        assert "foo bar baz" in result.data

    def test_grep_no_match(self, filesystem: FileSystem, sample_file: Path) -> None:
        """Test searching for a pattern with no matches."""
        result = filesystem.grep("xyz", str(sample_file))
        assert result.status == ToolStatus.SUCCESS
        assert result.data == ""

    def test_grep_case_insensitive(
        self, filesystem: FileSystem, temp_workspace: Path
    ) -> None:
        """Test case-insensitive search."""
        file_path = temp_workspace / "test.txt"
        file_path.write_text("Hello World\nhello world\n")

        result = filesystem.grep("HELLO", str(file_path), ignore_case=True)
        assert result.status == ToolStatus.SUCCESS
        assert "Hello" in result.data or "hello" in result.data

    def test_grep_recursive(self, filesystem: FileSystem, sample_dir: Path) -> None:
        """Test recursive search."""
        result = filesystem.grep("content", str(sample_dir), recursive=True)
        assert result.status == ToolStatus.SUCCESS
        assert "file1.txt" in result.data
        assert "file3.txt" in result.data


class TestTouch:
    """Tests for the touch command."""

    def test_touch_new_file(self, filesystem: FileSystem, temp_workspace: Path) -> None:
        """Test creating a new file."""
        file_path = temp_workspace / "new_file.txt"
        result = filesystem.touch(str(file_path))
        assert result.status == ToolStatus.SUCCESS
        assert file_path.exists()

    def test_touch_existing_file(
        self, filesystem: FileSystem, sample_file: Path
    ) -> None:
        """Test touching an existing file."""
        result = filesystem.touch(str(sample_file))
        assert result.status == ToolStatus.SUCCESS


class TestMkdir:
    """Tests for the mkdir command."""

    def test_mkdir_single(self, filesystem: FileSystem, temp_workspace: Path) -> None:
        """Test creating a single directory."""
        dir_path = temp_workspace / "new_dir"
        result = filesystem.mkdir(str(dir_path))
        assert result.status == ToolStatus.SUCCESS
        assert dir_path.is_dir()

    def test_mkdir_with_parents(
        self, filesystem: FileSystem, temp_workspace: Path
    ) -> None:
        """Test creating nested directories."""
        dir_path = temp_workspace / "a" / "b" / "c"
        result = filesystem.mkdir(str(dir_path), parents=True)
        assert result.status == ToolStatus.SUCCESS
        assert dir_path.is_dir()

    def test_mkdir_without_parents_fails(
        self, filesystem: FileSystem, temp_workspace: Path
    ) -> None:
        """Test that creating nested dirs without parents flag fails."""
        dir_path = temp_workspace / "x" / "y" / "z"
        result = filesystem.mkdir(str(dir_path), parents=False)
        assert result.status == ToolStatus.ERROR


class TestRm:
    """Tests for the rm command."""

    def test_rm_file(self, filesystem: FileSystem, sample_file: Path) -> None:
        """Test removing a file."""
        result = filesystem.rm(str(sample_file))
        assert result.status == ToolStatus.SUCCESS
        assert not sample_file.exists()

    def test_rm_directory_recursive(
        self, filesystem: FileSystem, sample_dir: Path
    ) -> None:
        """Test removing a directory recursively."""
        subdir = sample_dir / "subdir1"
        result = filesystem.rm(str(subdir), recursive=True)
        assert result.status == ToolStatus.SUCCESS
        assert not subdir.exists()

    def test_rm_directory_without_recursive(
        self, filesystem: FileSystem, sample_dir: Path
    ) -> None:
        """Test that removing a directory without recursive flag fails."""
        subdir = sample_dir / "subdir1"
        result = filesystem.rm(str(subdir), recursive=False)
        assert result.status == ToolStatus.ERROR
        assert subdir.exists()

    def test_rm_nonexistent_force(self, filesystem: FileSystem) -> None:
        """Test removing nonexistent file with force flag."""
        result = filesystem.rm("nonexistent.txt", force=True)
        assert result.status == ToolStatus.SUCCESS


class TestCpMv:
    """Tests for cp and mv commands."""

    def test_cp_file(
        self, filesystem: FileSystem, sample_file: Path, temp_workspace: Path
    ) -> None:
        """Test copying a file."""
        dest = temp_workspace / "copy.txt"
        result = filesystem.cp(str(sample_file), str(dest))
        assert result.status == ToolStatus.SUCCESS
        assert dest.exists()
        assert sample_file.exists()  # Original still exists

    def test_cp_directory(self, filesystem: FileSystem, sample_dir: Path) -> None:
        """Test copying a directory."""
        src = sample_dir / "subdir1"
        dest = sample_dir / "subdir1_copy"
        result = filesystem.cp(str(src), str(dest), recursive=True)
        assert result.status == ToolStatus.SUCCESS
        assert dest.is_dir()
        assert (dest / "file3.txt").exists()

    def test_mv_file(
        self, filesystem: FileSystem, sample_file: Path, temp_workspace: Path
    ) -> None:
        """Test moving a file."""
        dest = temp_workspace / "moved.txt"
        result = filesystem.mv(str(sample_file), str(dest))
        assert result.status == ToolStatus.SUCCESS
        assert dest.exists()
        assert not sample_file.exists()  # Original removed


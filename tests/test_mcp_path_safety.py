from __future__ import annotations

import pytest


def test_resolve_path_rejects_traversal(tmp_path) -> None:
    # Import the module, then override SKILLS_DIR for a deterministic sandbox
    import agent_skills.mcp.tools as mcp_tools

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    mcp_tools.SKILLS_DIR = skills_dir

    with pytest.raises(ValueError):
        mcp_tools.resolve_path("../escaped.txt")

    with pytest.raises(ValueError):
        mcp_tools.resolve_path("./../escaped.txt")

    with pytest.raises(ValueError):
        mcp_tools.resolve_path("skills/../escaped.txt")

    # Absolute path that looks like it's "under skills" but escapes after normalization
    with pytest.raises(ValueError):
        mcp_tools.resolve_path(str(skills_dir / ".." / "escaped.txt"))


def test_resolve_path_allows_in_root(tmp_path) -> None:
    import agent_skills.mcp.tools as mcp_tools

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    mcp_tools.SKILLS_DIR = skills_dir

    p = mcp_tools.resolve_path("sub/dir/file.txt")
    assert p.is_relative_to(skills_dir.resolve())

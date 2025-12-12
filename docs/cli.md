# CLI Reference

Agent Skills provides the `agent-skills` command-line tool to install, uninstall, list, and sync skills.

## Installation

The CLI is installed together with the `agent-skills` package:

```bash
uv sync
```

After installation, you can use the `agent-skills` command.

---

## Command overview

| Command | Description |
|--------|-------------|
| `agent-skills install <url>` | Install skill(s) from a Git repository |
| `agent-skills uninstall <name>` | Uninstall a skill |
| `agent-skills list` | List skills |
| `agent-skills sync-claude` | Sync Claude Code personal skills into agent-skills |

---

## Global options

| Option | Description |
|--------|-------------|
| `--dir, -d <path>` | Skills directory (default: `~/.agent-skills/skills/`) |
| `--version, -v` | Show version |
| `--help, -h` | Show help |

---

## `install` - Install skill(s)

Install skill(s) from a Git repository into your local skills directory.

### Syntax

```bash
agent-skills install <url> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `url` | Git repository URL (required) |

### Options

| Option | Description |
|--------|-------------|
| `--ref, -r <ref>` | Git ref (branch, tag, or commit hash) |
| `--name, -n <name>` | Custom skill name (only for single-skill repositories) |
| `--path, -p <path>` | Path within the repository (install skills from a subdirectory; uses sparse checkout) |
| `--dir, -d <path>` | Target skills directory |

### Examples

```bash
# Basic install
agent-skills install https://github.com/user/my-skill.git

# Install a specific version
agent-skills install https://github.com/user/my-skill.git --ref v1.0.0

# Install a specific branch
agent-skills install https://github.com/user/my-skill.git --ref main

# Use a custom name (single-skill repository)
agent-skills install https://github.com/user/my-skill.git --name custom-skill

# Install into a custom directory
agent-skills install https://github.com/user/my-skill.git --dir ./my-project/skills

# Install a skill from a subdirectory of a large repository (sparse checkout)
agent-skills install https://github.com/metabase/metabase.git --path .claude/skills/clojure-review
```

### Supported repository layouts

**Single-skill repository**: `SKILL.md` is at the repository root.

```
my-skill/
├── SKILL.md
├── scripts/
│   └── main.py
└── data/
```

**Multi-skill repository**: the repository contains multiple skill subdirectories.

```
skills-collection/
├── skill-a/
│   ├── SKILL.md
│   └── scripts/
├── skill-b/
│   ├── SKILL.md
│   └── scripts/
└── README.md
```

When installing a multi-skill repository, all subdirectories containing `SKILL.md` will be installed.

### Install from a large repository subdirectory

Some projects keep skills under a subdirectory (for example, [metabase](https://github.com/metabase/metabase)). Use `--path` to only download what you need instead of cloning the entire repository:

```bash
# Install a single skill directory
agent-skills install https://github.com/metabase/metabase.git --path .claude/skills/clojure-review

# Install multiple skills under a parent directory
agent-skills install https://github.com/metabase/metabase.git --path .claude/skills
```

**How it works**: `--path` uses Git sparse checkout to download only the specified path, which can significantly reduce download size and install time.

**Note**: `--path` expects a repository-relative path, not a GitHub web URL.

| GitHub web URL | Correct `--path` value |
|---|---|
| `https://github.com/metabase/metabase/tree/master/.claude/skills/clojure-review` | `.claude/skills/clojure-review` |
| `https://github.com/user/repo/tree/main/skills/my-skill` | `skills/my-skill` |

---

## `uninstall` - Uninstall a skill

Remove a skill directory from your skills directory.

### Syntax

```bash
agent-skills uninstall <name> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `name` | Skill name to uninstall (required) |

### Options

| Option | Description |
|--------|-------------|
| `--dir, -d <path>` | Skills directory |

### Examples

```bash
# Uninstall a skill
agent-skills uninstall my-skill

# Uninstall from a custom directory
agent-skills uninstall my-skill --dir ./my-project/skills
```

---

## `list` - List skills

List all skills in the skills directory.

### Syntax

```bash
agent-skills list [options]
```

### Options

| Option | Description |
|--------|-------------|
| `--installed, -i` | Only show skills installed via the CLI |
| `--dir, -d <path>` | Skills directory |

### Examples

```bash
# List all skills
agent-skills list

# List only skills installed via CLI
agent-skills list --installed

# List skills in a custom directory
agent-skills list --dir ./my-project/skills
```

### Output example

```
Skills in /Users/xxx/.agent-skills/skills:

  my-skill [installed]
    A useful skill for automation
    Source: https://github.com/user/my-skill.git @ v1.0.0

  pdf
    PDF processing toolkit

  skill-creator
    Meta-skill for creating new skills

Total: 3 skill(s), 1 installed via CLI
```

---

## `sync-claude` - Sync Claude Code personal skills

Sync Claude Code personal skills from `~/.claude/skills/` into the agent-skills skills directory. This helps you reuse skills you already maintain in the Claude Code ecosystem.

### Syntax

```bash
agent-skills sync-claude [options]
```

### Options

| Option | Description |
|--------|-------------|
| `--source, -s <path>` | Claude skills directory (default: `~/.claude/skills/`) |
| `--overwrite` | Overwrite existing skills with the same name |
| `--dry-run` | Show what would happen, without copying files |
| `--dir, -d <path>` | Target agent-skills skills directory |

### Examples

```bash
# Sync Claude Code personal skills to the default directory
agent-skills sync-claude

# Sync into a project-local skills directory (useful for MCP mounts)
agent-skills sync-claude --dir ./skills

# Overwrite existing skills
agent-skills sync-claude --overwrite

# Preview without copying
agent-skills sync-claude --dry-run
```

### Sync rules

- Scans **only the first-level subdirectories** under `--source`
- Only directories containing `SKILL.md` are synced
- Writes `.installed.json` metadata; `source` is recorded as `claude:<source_dir>` for traceability

---

## Skills directory

### Default location

By default, skills are installed to `~/.agent-skills/skills/`, which matches the recommended MCP mount path:

```json
{
  "mcpServers": {
    "agent-skills": {
      "args": ["-v", "~/.agent-skills/skills:/skills", ...]
    }
  }
}
```

### Custom location

Use `--dir` to install/manage skills in a different directory:

```bash
# Install into a project-local directory
agent-skills install https://github.com/user/skill.git --dir ./skills

# Install into another location
agent-skills install https://github.com/user/skill.git --dir /path/to/skills
```

---

## Installation metadata

Skills installed via the CLI include a `.installed.json` file with installation details:

```json
{
  "source": "https://github.com/user/my-skill.git",
  "ref": "v1.0.0",
  "installed_at": "2025-01-15T10:30:00+00:00",
  "commit": "abc1234def5",
  "path": ".claude/skills/my-skill"
}
```

> The `path` field is present only when installing with `--path`.

This metadata is used to:
- Distinguish manually added skills from CLI-installed skills
- Record installation source and version
- Enable future update functionality

---

## FAQ

### Q: Install failed with "git command not found"

**A**: Ensure Git is installed on your system:

```bash
# macOS
brew install git

# Ubuntu/Debian
sudo apt install git
```

### Q: How do I update an installed skill?

**A**: Currently, uninstall then reinstall:

```bash
agent-skills uninstall my-skill
agent-skills install https://github.com/user/my-skill.git --ref v2.0.0
```

### Q: A skill doesn’t show up in my agent after installing

**A**: Check:
1. The skills directory matches your MCP/Middleware configuration
2. If using MCP, restart the MCP server (restart Cursor / Claude Desktop)
3. The skill directory contains a valid `SKILL.md`

### Q: How do I view a skill’s details?

**A**: Use `skills_read` or open `SKILL.md` directly:

```bash
cat ~/.agent-skills/skills/my-skill/SKILL.md
```

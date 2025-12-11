# MCP Integration Guide

This document explains how to integrate Agent Skills via the MCP (Model Context Protocol) protocol.

## Overview

Agent Skills provides a standard MCP Server interface that can integrate with any MCP-compatible AI system:
- **Cursor** - AI programming assistant
- **Claude Desktop** - Anthropic's official desktop client
- Other MCP-compatible clients

---

## Quick Start

### Option A: Local Run (Recommended for Development)

No Docker required, run directly with `uv`:

```bash
# Install dependencies
uv sync

# Start MCP Server
uv run agent-skills-server
```

### Option B: Docker Run (Recommended for Production)

```bash
# Build image
docker build -t agent-skills:latest -f docker_config/Dockerfile .

# Run MCP Server
docker run -i --rm \
  -v ~/.agent-skills/skills:/skills \
  agent-skills:latest
```

---

## Cursor Configuration

Cursor configures MCP servers via `~/.cursor/mcp.json`.

### Configuration File Location

| System | Path |
|--------|------|
| macOS | `~/.cursor/mcp.json` |
| Windows | `%USERPROFILE%\.cursor\mcp.json` |
| Linux | `~/.cursor/mcp.json` |

### Configuration Example 1: Local Run (Simplest)

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/agent_skills",
        "agent-skills-server"
      ]
    }
  }
}
```

**Notes**:
- Uses `uv run` to start MCP Server directly
- No Docker required, suitable for development and debugging
- Skills directory uses the built-in `agent_skills/skills/`

### Configuration Example 2: Docker Run (Recommended)

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "~/.agent-skills/skills:/skills",
        "-v", "/Users:/Users",
        "agent-skills:latest"
      ]
    }
  }
}
```

The two mounts serve these purposes:
- `~/.agent-skills/skills:/skills` - Skills directory (required)
- `/Users:/Users` - Host file access (optional, for scripts to read/write external files)

> 💡 On Linux, change `/Users:/Users` to `/home:/home`

### Applying Configuration

1. Save the `mcp.json` file
2. **Completely restart Cursor** (Cmd+Q / Alt+F4)
3. Verify `skills_*` tools are available in Agent mode

---

## Claude Desktop Configuration

Claude Desktop configures MCP via `claude_desktop_config.json`.

### Configuration File Location

| System | Path |
|--------|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

### Configuration Example 1: Mount Skills Directory Only (Pure Skill Management)

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-v", "~/.agent-skills/skills:/skills",
               "agent-skills:latest"]
    }
  }
}
```

### Configuration Example 2: Mount Host Directory (Scripts Can Access External Files)

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-v", "~/.agent-skills/skills:/skills",
               "-v", "/Users:/Users",
               "agent-skills:latest"]
    }
  }
}
```

The two mounts serve these purposes:
- `~/.agent-skills/skills:/skills` - Skills directory (required)
- `/Users:/Users` - Host file access (optional, for scripts to read/write external files)

### Windows Path Example

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-v", "C:\\Users\\me\\.agent-skills\\skills:/skills",
               "-v", "C:\\Users:/Users",
               "agent-skills:latest"]
    }
  }
}
```

---

## Why Use Docker?

### 1. Isolated Execution Environment

Skills scripts may require various dependencies (like `pdf2image`, `pytesseract`). The Docker container comes with these tools pre-installed:

```
Pre-installed in Docker container:
├── Python 3.12 + uv
├── poppler-utils (PDF processing)
├── tesseract-ocr (OCR)
├── Node.js 20 (JavaScript tools)
└── Common Python libraries
```

### 2. Security

- Skills scripts execute inside the container, not affecting the host
- Only mounted directories are accessible
- Container is automatically destroyed after use (`--rm`)

### 3. Consistency

- Environment is the same regardless of host system
- Avoids "works on my machine" issues

### 4. When Docker Is Not Needed

- **During development/debugging**: Using `uv run` is faster
- **Pure computation skills only**: Like `gcd-calculator`, `prime-list-generator`
- **Agent has its own filesystem backend**: Like DeepAgent's FilesystemMiddleware

---

## Why Host Directory Mounting Is Needed?

### Scenario Analysis

| Scenario | Need Host Directory Mount? | Reason |
|----------|---------------------------|--------|
| Use `gcd-calculator` for GCD calculation | ❌ No | Pure computation, no file operations |
| Use `pdf` skill to convert PDF | ✅ Yes | Need to access user's PDF files |
| Create new skill | ❌ No | Skill is written to `/skills` directory |
| Generate report to user directory in a skill | ✅ Yes | Output file to user-specified path |

### How Host Mounting Works

```
Host Machine                    Docker Container
┌────────────────────┐         ┌────────────────────┐
│ /Users/xxx/        │ ──────► │ /Users/xxx/        │
│   ├── Desktop/     │   -v    │   ├── Desktop/     │
│   │   └── doc.pdf  │         │   │   └── doc.pdf  │
│   └── Documents/   │         │   └── Documents/   │
└────────────────────┘         └────────────────────┘

# skills_run uses absolute paths to access user files
skills_run(name="pdf", command="python scripts/convert.py /Users/xxx/Desktop/doc.pdf -o /Users/xxx/Desktop/doc.md")
```

### Without Host Directory Mounting

- Management tools (`skills_ls`, `skills_read`, etc.) can only operate on `/skills` directory
- `skills_run` scripts cannot access external files
- Suitable for pure skill management scenarios

---

## MCP Resources - Progressive Disclosure

Skills are automatically exposed to Agents as MCP Resources, enabling progressive disclosure:

```
Automatically loaded at startup (metadata):
┌─────────────────────────────────────────────────────────────┐
│  list_resources() returns:                                  │
│                                                             │
│  skill://skill-creator                                      │
│    description: Meta-skill for creating new skills          │
│                                                             │
│  skill://gcd-calculator                                     │
│    description: Calculate greatest common divisor           │
│                                                             │
│  skill://pdf                                                │
│    description: PDF processing skill                        │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ When Agent determines need
┌─────────────────────────────────────────────────────────────┐
│  read_resource("skill://skill-creator")                     │
│  → Returns complete SKILL.md content                        │
└─────────────────────────────────────────────────────────────┘
```

**Advantages:**
- Only skill names and descriptions loaded at startup (lightweight)
- Agent reads full content on demand (saves tokens)
- Automatically discovers newly added skills

---

## MCP Prompt

The system provides a built-in Prompt containing a complete skills system usage guide:

```python
# MCP client can retrieve
get_prompt("skill_guide")
```

Returns approximately 200 lines of detailed guidance, including:
- What are skills
- When to use skills
- How to use skills (4-step process)
- File system access rules
- 6 tools quick reference

---

## Command Line Arguments

```bash
agent-skills-server [OPTIONS]

Options:
  --skills-dir, -s PATH    Additional skills directory (can specify multiple times)
  --transport, -t TYPE     Transport protocol: stdio (default) or sse
  --quiet, -q              Quiet mode, no log output
```

### Examples

```bash
# Use SSE transport
uv run agent-skills-server --transport sse

# Add additional skills directory
uv run agent-skills-server --skills-dir /path/to/custom-skills

# Quiet mode
uv run agent-skills-server --quiet
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SKILLS_DIR` | `/skills` | Skills directory (required) |
| `DISABLE_BUILTIN_SKILLS` | `false` | Disable built-in skills loading |

### DISABLE_BUILTIN_SKILLS Explained

The Docker image includes multiple example skills (gcd-calculator, pdf, coprime-checker, etc.). This variable controls whether these built-in skills are loaded:

| Setting | Built-in Skills (gcd-calculator, pdf, etc.) | skill-creator Meta-skill |
|---------|---------------------------------------------|--------------------------|
| Not set (default) | ✅ Shown in resources list | ✅ Auto-copied to user /skills |
| `true` | ❌ Not shown | ✅ Still auto-copied to user /skills |

**Use Cases**:
- Want a clean skills directory containing only self-created skills
- But still need `skill-creator` to guide creating new skills

**Configuration Example**:

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-e", "DISABLE_BUILTIN_SKILLS=true",
               "-v", "~/.agent-skills/skills:/skills",
               "-v", "/Users:/Users",
               "agent-skills:latest"]
    }
  }
}
```

### Design Philosophy

- Management tools (`skills_ls`, `skills_read`, etc.) only operate on `/skills` directory
- External file access is achieved through `skills_run` command arguments and host directory mounting

---

## FAQ

### Q: Skills tools not available after Cursor restart?

**A**: Check the following:
1. Is `mcp.json` syntax correct (JSON format)
2. Are paths using absolute paths
3. Use Cmd+Q (macOS) or Alt+F4 (Windows) to completely quit Cursor, not just close the window

### Q: Docker container fails to start?

**A**: 
1. Ensure Docker Desktop is running
2. Ensure image is built: `docker images agent-skills:latest`
3. Check if mount paths exist

### Q: skills_run cannot access my files?

**A**: Need to mount host directory:
- macOS: Add `-v /Users:/Users`
- Linux: Add `-v /home:/home`
- Then use absolute paths in commands, like `skills_run(name="pdf", command="python scripts/convert.py /Users/xxx/file.pdf")`

### Q: Agent doesn't see newly added or deleted skills?

**A**: The MCP Server loads the skill list at startup. When you add or delete skills, you need to restart MCP for the Agent to see the changes:

- **Cursor**: Completely restart Cursor (Cmd+Q on macOS / Alt+F4 on Windows), then reopen
- **Claude Desktop**: Close and reopen Claude Desktop application

> 💡 **Note**: Modifying content within existing skills (like editing SKILL.md or scripts) usually doesn't require a restart, as skill content is read on demand. But adding new skills or deleting skills requires restarting MCP to refresh the skill list.

---

## Comparison with Middleware

| Feature | MCP | Middleware |
|---------|-----|------------|
| Protocol | JSON-RPC over stdio | Python native calls |
| Latency | Higher (inter-process communication) | Lower (direct calls) |
| Use Cases | Claude Desktop, Cursor | LangChain/LangGraph applications |
| Dependencies | mcp, fastmcp | docker (Python SDK) |
| Configuration Complexity | JSON config file | Python code |

If you're developing a LangChain application, we recommend using [Middleware Integration](middleware-integration.md).

# Tools Reference

Agent Skills provides 6 unified prefix tools with atomic functionality. The MCP and Middleware interfaces are consistent.

## Tools Overview

| Tool | Function | Scope |
|------|----------|-------|
| `skills_ls` | List files and directories | /skills directory only |
| `skills_read` | Read file contents | /skills directory only |
| `skills_write` | Write files | /skills directory only |
| `skills_create` | Create new skills | /skills directory only |
| `skills_run` | Run skill scripts | Can access external files via command arguments |
| `skills_bash` | Execute shell commands | /skills directory only |

> **Note**: Management tools can only operate on the `/skills` directory. To access external files, use `skills_run` and pass absolute paths in command arguments.

---

## skills_ls - List Files

List directory contents. This tool can only operate on the `/skills` directory.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | `""` | Path to list (within /skills only) |

### Path Rules

| Path | Description |
|------|-------------|
| `""` | List /skills root directory |
| `"skills"` | List all available skills |
| `"skills/<name>"` | List files in a specific skill |
| `"./xxx"` or `"xxx"` | Relative to /skills |

### Examples

```python
skills_ls()                              # List /skills directory
skills_ls(path="skills")                 # List all skills
skills_ls(path="skills/gcd-calculator")  # List files in a skill
```

---

## skills_read - Read Files

Read text file contents. This tool can only operate on the `/skills` directory.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | File path (required, within /skills only) |

### Path Rules

Same as `skills_ls`, can only access the `/skills` directory.

### Examples

```python
skills_read(path="skills/gcd-calculator/SKILL.md")       # Read skill documentation
skills_read(path="skills/gcd-calculator/scripts/gcd.py") # Read script
```

---

## skills_write - Write Files

Write or overwrite file contents, automatically creates parent directories. This tool can only operate on the `/skills` directory.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | File path (required, within /skills only) |
| `content` | string | File content (required) |

### Examples

```python
skills_write(path="skills/my-skill/scripts/run.py", content="print('hi')")
skills_write(path="skills/my-skill/data/config.json", content="{...}")
```

---

## skills_create - Create Skills

Create a new skill directory and SKILL.md file.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Skill name (lowercase letters, numbers, hyphens) |
| `description` | string | One-line description |
| `instructions` | string | Markdown content for SKILL.md |

### Naming Rules

- Must start with a lowercase letter
- Can only contain lowercase letters, numbers, and hyphens
- Valid: `code-reviewer`, `data-analyzer`, `pdf2image`
- Invalid: `Code-Reviewer`, `dataAnalyzer`, `my_tool`

### Examples

```python
skills_create(
    name="my-tool",
    description="Does something useful",
    instructions="# My Tool\n\n## Usage\nRun `skills_run(name=\"my-tool\", command=\"python scripts/main.py\")`"
)
```

---

## skills_run - Run Skill Scripts

Execute commands in a skill directory. If `scripts/pyproject.toml` exists, it will automatically use `uv` to create an isolated environment.

**This is the only tool that can access external files**, by passing absolute paths in command arguments.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | - | Skill name (required) |
| `command` | string | - | Command to execute (required, can include absolute paths) |
| `timeout` | int | 120 | Timeout in seconds |

### Execution Mechanism

```
skills_run(name="pdf", command="python scripts/convert.py /Users/xxx/input.pdf")
           │
           ▼
┌─────────────────────────────────────────┐
│ Check if scripts/pyproject.toml exists │
└─────────────────────────────────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
 Exists       Not Exists
    │             │
    ▼             ▼
uv sync       Execute
uv run        command
              directly
```

### Examples

```python
skills_run(name="gcd-calculator", command="python scripts/gcd.py 12 18")
skills_run(name="my-tool", command="bash scripts/setup.sh", timeout=120)
# Process host machine files (requires mounting the corresponding directory)
skills_run(name="pdf", command="python scripts/convert.py /Users/xxx/doc.pdf -o /Users/xxx/doc.md")
```

---

## skills_bash - Execute Commands

Execute general shell commands in the /skills directory. This tool can only operate on the `/skills` directory.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `command` | string | - | Command to execute (required) |
| `timeout` | int | 60 | Timeout in seconds |
| `cwd` | string | `""` | Working directory (within /skills only) |

### Examples

```python
skills_bash(command="ls -la")                           # List /skills directory
skills_bash(command="grep -r 'pattern' .", cwd="skills/my-skill")  # Search in skill directory
skills_bash(command="rm -rf old-file.txt", cwd="skills/my-skill")  # Delete file
```

---

## File Access Workflow

Agents can access host machine files using absolute paths (requires mounting the corresponding directory):

```
1. User request: "Help me process /Users/me/doc.pdf"
2. skills_read("skills/pdf/SKILL.md") → Learn processing method
3. skills_run("pdf", "python scripts/convert.py /Users/me/doc.pdf -o /Users/me/doc.md")
4. Result is generated directly at host /Users/me/doc.md
5. Agent informs user of result location
```

---

## Tool Permissions

| Tool | Scope | Description |
|------|-------|-------------|
| `skills_ls/read/write/create/bash` | /skills directory only | For skill management |
| `skills_run` | Can access any mounted path | Pass absolute paths via command arguments |

# Skill Format

This document explains how to write and organize Skills (skill packages).

## Overview

A Skill is a complete directory structure containing guides, scripts, and data that teaches an Agent how to complete specific tasks.

## Directory Structure

```
my-skill/
├── SKILL.md          # Entry guide (required)
├── scripts/          # Executable scripts
│   ├── main.py
│   └── pyproject.toml  # Dependency configuration (auto-generated)
├── data/             # Templates and data files
│   └── template.txt
├── docs/             # Detailed documentation (optional)
│   └── advanced.md
└── examples/         # Example files
    └── sample.json
```

---

## SKILL.md Format

SKILL.md is the entry document for a skill, using YAML frontmatter + Markdown.

### Basic Structure

```markdown
---
name: my-skill
description: Brief function description (one sentence)
---

# Skill Name

## Overview
What this skill does, what scenarios it's suitable for.

## Usage

### Basic Usage
\`\`\`
skills_run(name="my-skill", command="python scripts/main.py <args>")
\`\`\`

### Parameter Description
- `<input>`: Input file path
- `--output`: Output file path (optional)

## Script Description

| Script | Function |
|--------|----------|
| `scripts/main.py` | Main logic script |

## Examples

Input: ...
Output: ...

## Notes
- Note 1
- Note 2
```

### YAML Frontmatter

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Skill unique identifier, matches directory name |
| `description` | Yes | Short description, displayed in skill list |

### Naming Rules

- Must start with a lowercase letter
- Can only contain lowercase letters, numbers, and hyphens
- Valid: `code-reviewer`, `data-analyzer`, `pdf2image`
- Invalid: `Code-Reviewer`, `dataAnalyzer`, `my_tool`

---

## Script Writing

### Python Script Template

```python
#!/usr/bin/env python3
"""Script function description"""
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Script function")
    parser.add_argument("input", help="Input file")
    parser.add_argument("-o", "--output", help="Output file", default="-")
    args = parser.parse_args()
    
    # Processing logic...
    result = process(args.input)
    
    if args.output == "-":
        print(result)
    else:
        with open(args.output, "w") as f:
            f.write(result)

if __name__ == "__main__":
    main()
```

### Dependency Management

If scripts require third-party libraries, edit `scripts/pyproject.toml`:

```toml
[project]
name = "my-skill-scripts"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "requests>=2.28",
    "pandas>=2.0",
]

[tool.uv]
managed = true
```

When `skills_run` executes a skill with `pyproject.toml`, it automatically uses `uv` to create an isolated environment.

---

## Creating Skills

### Using skills_create

```python
skills_create(
    name="my-tool",
    description="Does something useful",
    instructions="# My Tool\n\n## Usage\n..."
)
```

### Adding Scripts

```python
skills_write(
    path="skills/my-tool/scripts/main.py",
    content="#!/usr/bin/env python3\nprint('Hello')"
)
```

### Adding Data Files

```python
skills_write(
    path="skills/my-tool/data/template.txt",
    content="Template content here"
)
```

---

## Meta-skill: skill-creator

The system includes the `skill-creator` meta-skill, which teaches Agents how to create new skills.

When using a custom skills directory, `skill-creator` is automatically copied to that directory.

View meta-skill:

```python
skills_read(path="skills/skill-creator/SKILL.md")
```

---

## Project Structure

```
agent_skills/
├── agent_skills/
│   ├── core/
│   │   ├── skill_manager.py  # Skill discovery and management
│   │   ├── types.py          # Type definitions
│   │   ├── middleware.py     # LangChain Middleware integration
│   │   ├── docker_runner.py  # Docker container management
│   │   └── tools_factory.py  # LangChain tools factory
│   ├── mcp/
│   │   ├── server.py         # MCP Server entry
│   │   ├── tools.py          # 6 skills_* tools (MCP)
│   │   └── prompts.py        # Skill Guide Prompt
│   └── skills/               # Built-in skills
│       ├── skill-creator/    # Meta-skill for creating skills
│       ├── gcd-calculator/   # Greatest common divisor calculation
│       ├── pdf/              # PDF processing
│       └── ...
├── docker_config/
│   └── Dockerfile
├── examples/
│   ├── demo_skills.py        # Local Demo
│   ├── demo_with_docker.py   # Docker Demo
│   ├── demo_deepagent.py     # Deep Agent + MCP Demo
│   └── demo_middleware.py    # Deep Agent + Middleware Demo
├── docs/                     # Documentation
├── tests/
├── pyproject.toml
└── README.md
```

---

## Best Practices

### Documentation Writing

- Get straight to the point: First paragraph clearly states what the skill does
- Copyable commands: Example commands can be used directly
- Clear parameters: List all parameters and their meanings
- Input/output examples: Let users know expected results

### Script Writing

- Use `argparse` for parameter handling
- Support stdin/stdout (use `-` to indicate)
- Prefer standard library, minimize dependencies
- Add clear error messages

### Directory Organization

- Scripts go in `scripts/` directory
- Templates and configurations go in `data/` directory
- Detailed documentation goes in `docs/` directory
- Example files go in `examples/` directory

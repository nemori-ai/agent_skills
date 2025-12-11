---
name: skill-creator
description: Meta-skill for creating complex skill packages with scripts, data, and multi-file structures
---

# Skill Creator

This skill teaches you how to create **Skill Packages**—complete directory structures containing guides, scripts, and data.

## ⚠️ Path Guidelines

> **Rule**: Scripts should accept output path parameters, letting callers specify output locations. Skill directories only store code.
>
> For detailed guidelines: `skills_read(path="skills/skill-creator/docs/script-guidelines.md")`

## What is a Skill Package?

A skill package is not just a Markdown file, but a complete directory structure:

```
skill-name/
├── SKILL.md          # Entry guide (required)
├── scripts/          # Executable scripts
│   ├── main.py
│   └── pyproject.toml  (dependency config)
├── data/             # Templates and data files
└── docs/             # Detailed documentation (optional)
```

---

## 📖 Choose Guide by Scenario

Based on your needs, read the corresponding detailed documentation:

### 🆕 Create New Skill from Scratch

First time creating a skill package, learn the complete process (5-step creation method).

```python
skills_read(path="skills/skill-creator/docs/quick-start.md")
```

### 📝 Write/Modify SKILL.md Documentation

Learn the structure and template for SKILL.md.

```python
skills_read(path="skills/skill-creator/docs/skillmd-template.md")
```

### 🔧 Add Scripts to Skill

Learn Python/Bash script writing standards and dependency management.

```python
skills_read(path="skills/skill-creator/docs/script-guidelines.md")
```

### 🔄 Script Debugging Failed, Need Iteration

How to properly clean up old versions after creating replacement scripts.

```python
skills_read(path="skills/skill-creator/docs/iteration-and-cleanup.md")
```

### 📚 View Complete Example

Reference a complete skill creation process (code reviewer skill).

```python
skills_read(path="skills/skill-creator/docs/full-example.md")
```

---

## Command Quick Reference

| Tool | Purpose | Example |
|------|---------|---------|
| `skills_ls(path="skills")` | List all skills | View available skills |
| `skills_ls(path="skills/<name>")` | List files in skill | Check file structure |
| `skills_read(path="skills/<name>/SKILL.md")` | Read skill documentation | Learn skill usage |
| `skills_create(name, description, instructions)` | Create skill skeleton | Create new skill |
| `skills_write(path, content)` | Add/overwrite file | Add script |
| `skills_run(name, command)` | Execute skill command | Test script |
| `skills_bash(command, cwd)` | Execute shell command | Delete/rename file |

---

## Quick Start

Creating the simplest skill requires only 2 steps:

```python
# 1. Create skill skeleton
skills_create(
    name="hello-world",
    description="Example skill",
    instructions="# Hello World\n\nRun `skills_run(name=\"hello-world\", command=\"python scripts/hello.py\")`"
)

# 2. Add script
skills_write(
    path="skills/hello-world/scripts/hello.py",
    content='print("Hello, World!")'
)

# 3. Test
skills_run(name="hello-world", command="python scripts/hello.py")
```

Need more detailed guidance? Read [Quick Start Guide](docs/quick-start.md).

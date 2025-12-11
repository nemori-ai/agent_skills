# Quick Start: Create Skills from Scratch

This guide helps you create your first skill package in 5 minutes.

## Creation Process Overview

```
1. skills_create()     → Create skill skeleton
2. skills_write()      → Add script files
3. skills_write()      → Add data/templates (optional)
4. skills_ls()         → View file structure
5. skills_run()        → Test run
```

---

## Step 1: Create Skill Skeleton

Use `skills_create` to create the basic structure:

```python
skills_create(
    name="my-analyzer",
    description="Analyze data files and generate reports",
    instructions="# Data Analyzer\n\n## Usage\nRun `skills_run(name=\"my-analyzer\", command=\"python scripts/analyze.py <file>\")`"
)
```

### Naming Conventions

| Rule | Correct Example | Wrong Example |
|------|-----------------|---------------|
| Use lowercase letters | `code-reviewer` | `Code-Reviewer` |
| Separate words with hyphens | `data-analyzer` | `dataAnalyzer` |
| Can include numbers | `pdf2image` | `pdf_to_image` |

---

## Step 2: Add Script

Use `skills_write` to add executable scripts:

```python
skills_write(
    path="skills/my-analyzer/scripts/analyze.py",
    content='''#!/usr/bin/env python3
"""Data analysis script"""
import sys
import json

def analyze(filepath):
    with open(filepath) as f:
        data = json.load(f)
    # Analysis logic...
    print(f"Analyzed {len(data)} records")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: analyze.py <file>")
        sys.exit(1)
    analyze(sys.argv[1])
'''
)
```

> **Tip**: When you add `.py` files to the `scripts/` directory, the system automatically generates `pyproject.toml` for dependency management.

---

## Step 3: Add Data/Templates (Optional)

If the skill needs templates or configuration files:

```python
skills_write(
    path="skills/my-analyzer/data/report_template.md",
    content="# Analysis Report\n\nDate: {{date}}\n\n## Results\n{{results}}"
)
```

---

## Step 4: View and Verify

Confirm the file structure is correct:

```python
# View skill directory structure
skills_ls(path="skills/my-analyzer")

# Read specific file content
skills_read(path="skills/my-analyzer/scripts/analyze.py")
```

Expected structure:
```
my-analyzer/
├── SKILL.md
├── scripts/
│   ├── analyze.py
│   └── pyproject.toml  (auto-generated)
└── data/
    └── report_template.md
```

---

## Step 5: Test Run

Execute script to verify functionality:

```python
skills_run(name="my-analyzer", command="python scripts/analyze.py /workspace/sample.json")
```

> ⚠️ **Path Guidelines**: Input/output files should use absolute paths. Do not save user files to skill directory!
> See [Script Writing Guidelines](script-guidelines.md) for details.

### Common Issues

| Issue | Solution |
|-------|----------|
| Missing dependency | Edit `scripts/pyproject.toml` to add dependencies |
| Script execution failed | Check if paths and arguments are correct |
| Permission issues | Ensure script has execution permissions |
| Files saved to skill directory | Use absolute paths for output |

---

## Next Steps

- 📝 **Improve documentation**: Read [SKILL.md Writing Template](skillmd-template.md)
- 🔧 **Add more scripts**: Read [Script Writing Guidelines](script-guidelines.md)
- 📚 **Reference complete case**: Read [Complete Example](full-example.md)

# SKILL.md Writing Template

SKILL.md is the entry document for a skill, telling users what this skill does and how to use it.

## Required Structure

### 1. YAML Frontmatter (Required)

File must begin with YAML frontmatter:

```yaml
---
name: skill-name
description: Brief function description (one sentence explaining skill purpose)
---
```

**Field descriptions**:
- `name`: Skill unique identifier, must match directory name
- `description`: Brief shown in skill list (recommended < 50 characters)

---

### 2. Document Body Structure

Recommended structure for organizing content:

```markdown
# Skill Name

One or two sentences summarizing the core function and applicable scenarios.

## Dependencies

- Python 3.12+
- Third-party libraries: pandas, requests (if any)

## Usage

### Basic Usage

```
skills_run(name="skill-name", command="python scripts/main.py <args>")
```

### Parameter Description

| Parameter | Description | Default |
|-----------|-------------|---------|
| `<input>` | Input file path | Required |
| `--output`, `-o` | Output file path | stdout |
| `--verbose`, `-v` | Show detailed info | false |

## Script Description

| Script | Function |
|--------|----------|
| `scripts/main.py` | Main logic script |
| `scripts/helpers.sh` | Helper tools (optional) |

## Examples

### Input
```json
{"name": "test", "value": 123}
```

### Command
```
skills_run(name="skill-name", command="python scripts/main.py input.json -o output.txt")
```

### Output
```
Processing complete: 1 record
```

## Notes

- Input file must be valid JSON format
- Large file processing may take longer
- Does not support data structures nested more than 10 levels
```

---

## Writing Guidelines

### ✅ Good SKILL.md

- **Get to the point**: First paragraph clearly states what skill does
- **Copyable commands**: Example commands can be used directly
- **Clear parameters**: List all parameters and their meanings
- **Input/output examples**: Let users know expected results

### ❌ Avoid These

- Lengthy background introductions
- Missing executable command examples
- Incomplete parameter descriptions
- No mention of dependencies and limitations

---

## Quick Copy Template

```markdown
---
name: my-skill
description: One sentence describing skill function
---

# Skill Name

Core function description of the skill.

## Usage

```
skills_run(name="my-skill", command="python scripts/main.py <input>")
```

## Parameter Description

- `<input>`: Input file path

## Examples

Input: `data.json`
Output: Processing result

## Notes

- Note 1
- Note 2
```

# Script Iteration and Cleanup Guidelines

When developing skill scripts, you may go through multiple iterations—the first version may not execute properly due to dependency issues, excessive complexity, or other reasons.

**Core Principle: When you create a replacement script, you must clean up the failed old scripts.**

---

## ❌ Wrong Approach

```
my-skill/scripts/
├── convert.py              # First version, dependency issues, won't execute
├── convert_v2.py           # Second version, still has problems
├── convert_simple.py       # Third version, works
└── pyproject.toml
```

**Problems**:
- Messy directory, hard to maintain
- Future users don't know which script to use
- SKILL.md instructions may not match actual working scripts

---

## ✅ Correct Approach

### Method 1: Delete Failed Scripts

After verifying new script works, delete all failed versions:

```python
# Delete failed scripts
skills_bash(command="rm scripts/convert.py scripts/convert_v2.py", cwd="skills/my-skill")
```

### Method 2: Rename to Main Script

If there was originally a "main script name", rename the successful version:

```python
# Rename successful script to main script name
skills_bash(command="mv scripts/convert_simple.py scripts/convert.py", cwd="skills/my-skill")

# Delete old failed versions (if any)
skills_bash(command="rm -f scripts/convert_v2.py", cwd="skills/my-skill")
```

### Method 3: Update SKILL.md

If you decide to keep the new script name, ensure documentation is updated:

```python
# Read current SKILL.md
skills_read(path="skills/my-skill/SKILL.md")

# Modify command examples in documentation to point to correct script
skills_write(path="skills/my-skill/SKILL.md", content="""...(updated content)""")
```

---

## Cleanup Checklist

After completing skill creation, perform these checks:

### 1. Check File Structure

```python
skills_ls(path="skills/<name>/scripts")
```

Confirm:
- [ ] Only contains usable scripts
- [ ] No leftover files with `_old`, `_backup`, `_v2`, `_simple` or other temporary names

### 2. Check Documentation Consistency

```python
skills_read(path="skills/<name>/SKILL.md")
```

Confirm:
- [ ] Command examples in documentation point to actually existing scripts
- [ ] Parameter descriptions match actual script parameters

### 3. Verify Script Executes

```python
skills_run(name="<name>", command="python scripts/main.py --help")
```

Confirm:
- [ ] Script executes normally
- [ ] Help information displays correctly

---

## Why This Matters?

Skill packages are **reusable capability modules**. A clean, accurately documented skill package:

| Benefit | Description |
|---------|-------------|
| Easy to understand | Other Agents or users can quickly get started |
| Avoid confusion | Won't accidentally execute failed scripts |
| Professional standards | Demonstrates good development practices |
| Easy to maintain | Later modifications won't be disrupted by historical files |

---

## Iterative Development Suggestions

If scripts are expected to require multiple iterations:

1. **Verify ideas with simple version first**: Start with the simplest implementation
2. **Add complexity after successful verification**: Gradually add features
3. **Clean up promptly**: Clean up old versions immediately after each successful iteration
4. **Maintain single entry point**: Keep only one main script in the end

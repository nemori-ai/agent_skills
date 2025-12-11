# Script Writing Guidelines

This guide explains how to write high-quality skill scripts.

## Python Script Template

```python
#!/usr/bin/env python3
"""Brief script function description"""
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Script function description")
    parser.add_argument("input", help="Input file path")
    parser.add_argument("-o", "--output", help="Output file path", default="-")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed info")
    args = parser.parse_args()
    
    # Read input
    if args.input == "-":
        data = sys.stdin.read()
    else:
        with open(args.input) as f:
            data = f.read()
    
    # Processing logic
    result = process(data)
    
    # Output result
    if args.output == "-":
        print(result)
    else:
        with open(args.output, "w") as f:
            f.write(result)

def process(data: str) -> str:
    """Core processing logic"""
    # Implement processing logic
    return data

if __name__ == "__main__":
    main()
```

### Python Script Key Points

| Point | Description |
|-------|-------------|
| Use `argparse` | Standardized parameter handling, auto-generates help info |
| Support stdin/stdout | Use `-` for standard input/output, convenient for pipe operations |
| Prefer standard library | Reduce dependencies, improve portability |
| Clear error messages | Help users locate issues |

---

## Bash Script Template

```bash
#!/bin/bash
# Script function description

set -e  # Exit on error
set -u  # Error on undefined variable

# Parameter check
if [ $# -lt 1 ]; then
    echo "Usage: $0 <input> [output]" >&2
    exit 1
fi

INPUT="$1"
OUTPUT="${2:-/dev/stdout}"

# Check input file
if [ ! -f "$INPUT" ]; then
    echo "Error: File not found - $INPUT" >&2
    exit 1
fi

# Processing logic
cat "$INPUT" | some_command > "$OUTPUT"

echo "Done: $INPUT -> $OUTPUT" >&2
```

### Bash Script Key Points

| Point | Description |
|-------|-------------|
| `set -e` | Exit immediately on command failure |
| `set -u` | Error on undefined variable usage |
| Parameter check | Verify required parameters are provided |
| Error output to stderr | Use `>&2` to output errors to stderr |

---

## Dependency Management

When scripts require third-party libraries, edit `scripts/pyproject.toml`:

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

> **Execution mechanism**: `skills_run` detects `pyproject.toml` and automatically runs `uv sync` to install dependencies, then executes the script in an isolated environment.

---

## ⚠️ File Path Handling (Very Important)

### Path Guidelines

| Path | Purpose | Example |
|------|---------|---------|
| `/skills/` | **Only store skill code** | `/skills/my-skill/scripts/main.py` |
| Absolute paths | **User files (specified by caller)** | `/Users/xxx/Desktop/output.pdf` |

### Core Rules

1. **Scripts should accept input/output paths as command-line arguments**
2. **Don't hardcode output paths, let callers decide**
3. **Skill directory only contains code, documentation, and templates**

### Why This Design?

- Skill directories may be shared across multiple users/sessions
- Saving output files to skill directory pollutes skill code
- Callers know where files should be saved

### Input Files

When script runs, working directory is the skill directory (e.g., `/skills/my-skill/`).

```python
# ✅ Correct: Receive external file path via parameter
input_path = args.input  # e.g., "/Users/xxx/data.json"

# ✅ Correct: Use relative path for internal skill templates
template_path = "data/template.md"
```

### Output Files

**Receive** output path via parameter:

```python
# ✅ Correct: Caller specifies output location
output_path = args.output  # e.g., "/Users/xxx/Desktop/result.txt"

# ❌ Wrong: Don't hardcode paths
# output_path = "result.txt"  # Will save to skill directory!
```

### Handling Paths in Scripts

```python
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input file path")
    parser.add_argument("-o", "--output", required=True, 
                        help="Output file path")
    args = parser.parse_args()
    
    # Use paths provided by caller directly
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # ... processing logic
```

### Examples in SKILL.md

```python
# ✅ Correct example: Use absolute paths
skills_run(name="pdf-converter", command="python scripts/convert.py /Users/xxx/input.pdf -o /Users/xxx/output.pdf")

# ❌ Wrong example: Use relative paths
skills_run(name="pdf-converter", command="python scripts/convert.py input.pdf -o output.pdf")
# Files will be saved to /skills/pdf-converter/output.pdf (pollutes skill directory!)
```

---

## Error Handling Best Practices

```python
import sys

def main():
    try:
        result = do_work()
        print(result)
    except FileNotFoundError as e:
        print(f"Error: File not found - {e.filename}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: Invalid data format - {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

**Exit code conventions**:
- `0`: Success
- `1`: General error
- `2`: Argument/input error

# 脚本编写规范

本指南介绍如何编写高质量的技能脚本。

## Python 脚本模板

```python
#!/usr/bin/env python3
"""脚本功能简述"""
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="脚本功能描述")
    parser.add_argument("input", help="输入文件路径")
    parser.add_argument("-o", "--output", help="输出文件路径", default="-")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")
    args = parser.parse_args()
    
    # 读取输入
    if args.input == "-":
        data = sys.stdin.read()
    else:
        with open(args.input) as f:
            data = f.read()
    
    # 处理逻辑
    result = process(data)
    
    # 输出结果
    if args.output == "-":
        print(result)
    else:
        with open(args.output, "w") as f:
            f.write(result)

def process(data: str) -> str:
    """核心处理逻辑"""
    # 实现处理逻辑
    return data

if __name__ == "__main__":
    main()
```

### Python 脚本要点

| 要点 | 说明 |
|------|------|
| 使用 `argparse` | 标准化参数处理，自动生成帮助信息 |
| 支持 stdin/stdout | 使用 `-` 表示标准输入/输出，便于管道操作 |
| 优先使用标准库 | 减少依赖，提高可移植性 |
| 清晰的错误信息 | 帮助用户定位问题 |

---

## Bash 脚本模板

```bash
#!/bin/bash
# 脚本功能描述

set -e  # 出错时退出
set -u  # 使用未定义变量时报错

# 参数检查
if [ $# -lt 1 ]; then
    echo "Usage: $0 <input> [output]" >&2
    exit 1
fi

INPUT="$1"
OUTPUT="${2:-/dev/stdout}"

# 检查输入文件
if [ ! -f "$INPUT" ]; then
    echo "Error: File not found - $INPUT" >&2
    exit 1
fi

# 处理逻辑
cat "$INPUT" | some_command > "$OUTPUT"

echo "Done: $INPUT -> $OUTPUT" >&2
```

### Bash 脚本要点

| 要点 | 说明 |
|------|------|
| `set -e` | 命令失败时立即退出 |
| `set -u` | 使用未定义变量时报错 |
| 参数检查 | 验证必需参数是否提供 |
| 错误输出到 stderr | 使用 `>&2` 将错误信息输出到 stderr |

---

## 依赖管理

当脚本需要第三方库时，编辑 `scripts/pyproject.toml`：

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

> **执行机制**：`skills_run` 检测到 `pyproject.toml` 后会自动执行 `uv sync` 安装依赖，然后在隔离环境中运行脚本。

---

## ⚠️ 文件路径处理（非常重要）

### 路径规范

| 路径 | 用途 | 示例 |
|------|------|------|
| `/skills/` | **只存放技能代码** | `/skills/my-skill/scripts/main.py` |
| 绝对路径 | **用户文件（由调用者指定）** | `/Users/xxx/Desktop/output.pdf` |

### 核心规则

1. **脚本应接受输入/输出路径作为命令行参数**
2. **不要硬编码输出路径，由调用者决定**
3. **技能目录只包含代码、文档和模板**

### 为什么这样设计？

- 技能目录会被多个用户/会话共享
- 将输出文件保存到技能目录会污染技能代码
- 调用者知道文件应该保存到哪里

### 输入文件

脚本运行时，工作目录是技能目录（如 `/skills/my-skill/`）。

```python
# ✅ 正确：通过参数接收外部文件路径
input_path = args.input  # 如 "/Users/xxx/data.json"

# ✅ 正确：技能内部模板使用相对路径
template_path = "data/template.md"
```

### 输出文件

**通过参数接收**输出路径：

```python
# ✅ 正确：由调用者指定输出位置
output_path = args.output  # 如 "/Users/xxx/Desktop/result.txt"

# ❌ 错误：不要硬编码路径
# output_path = "result.txt"  # 会保存到技能目录！
```

### 在脚本中处理路径

```python
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="输入文件路径")
    parser.add_argument("-o", "--output", required=True, 
                        help="输出文件路径")
    args = parser.parse_args()
    
    # 直接使用调用者提供的路径
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # ... 处理逻辑
```

### 在 SKILL.md 中的示例

```python
# ✅ 正确示例：使用绝对路径
skills_run(name="pdf-converter", command="python scripts/convert.py /Users/xxx/input.pdf -o /Users/xxx/output.pdf")

# ❌ 错误示例：使用相对路径
skills_run(name="pdf-converter", command="python scripts/convert.py input.pdf -o output.pdf")
# 文件会被保存到 /skills/pdf-converter/output.pdf（污染技能目录！）
```

---

## 错误处理最佳实践

```python
import sys

def main():
    try:
        result = do_work()
        print(result)
    except FileNotFoundError as e:
        print(f"错误: 文件不存在 - {e.filename}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"错误: 数据格式无效 - {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
```

**退出码约定**：
- `0`：成功
- `1`：一般错误
- `2`：参数/输入错误


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

## 文件路径处理

### 输入文件

脚本运行时，工作目录是技能目录（如 `/skills/my-skill/`）。

处理用户工作空间文件时，使用 `/workspace/` 前缀：

```python
# 用户文件在 /workspace/ 下
input_path = "/workspace/data.json"

# 技能内部文件使用相对路径
template_path = "data/template.md"
```

### 输出文件

推荐输出到 `/workspace/`，便于用户访问：

```python
output_path = "/workspace/output/result.txt"
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


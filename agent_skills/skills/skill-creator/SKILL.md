---
name: skill-creator
description: 用于创建复杂技能包的元技能，包含脚本、数据和多文件结构
---

# 技能创建器

本技能教你如何创建**技能包 (Skill Package)**——一个包含指南、脚本和数据的完整目录结构。

## 什么是技能包？

技能包不仅仅是一个 Markdown 文件，而是一个完整的目录结构：

```
skill-name/
├── SKILL.md          # 入口指南 (必需)
├── scripts/          # 可执行脚本
│   ├── main.py       # 主脚本
│   └── helpers.sh    # 辅助脚本
├── data/             # 模板和数据文件
│   └── template.txt
└── examples/         # 示例文件
    └── sample.json
```

## 创建技能包的流程

### 第一步：创建技能骨架

```python
skills_create(
    name="my-analyzer",
    description="分析数据文件并生成报告",
    instructions="# 数据分析器\n\n## 使用方法\n运行 `skills_run(name=\"my-analyzer\", command=\"python scripts/analyze.py <file>\")`"
)
```

**命名规范：**
- 使用小写字母、数字和连字符
- 正确：`code-reviewer`, `data-analyzer`
- 错误：`Code Reviewer`, `dataAnalyzer`

### 第二步：添加脚本

```python
skills_write(
    name="my-analyzer",
    file="scripts/analyze.py",
    content='''#!/usr/bin/env python3
"""数据分析脚本"""
import sys
import json

def analyze(filepath):
    with open(filepath) as f:
        data = json.load(f)
    # 分析逻辑...
    print(f"分析了 {len(data)} 条记录")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: analyze.py <file>")
        sys.exit(1)
    analyze(sys.argv[1])
'''
)
```

### 第三步：添加数据/模板

```python
skills_write(
    name="my-analyzer", 
    file="data/report_template.md",
    content="# 分析报告\n\n日期: {{date}}\n\n## 结果\n{{results}}"
)
```

### 第四步：查看和验证

```python
# 查看文件结构
skills_list(name="my-analyzer")

# 读取特定文件
skills_read(name="my-analyzer", file="scripts/analyze.py")
```

### 第五步：测试运行

```python
skills_run(name="my-analyzer", command="python scripts/analyze.py examples/sample.json")
```

---

## 编写 SKILL.md

SKILL.md 是技能的入口文档，必须包含：

### 1. YAML Frontmatter

```yaml
---
name: skill-name
description: 简洁的功能描述
---
```

### 2. 结构化内容

```markdown
# 技能名称

## 概述
这个技能做什么，适用于什么场景。

## 依赖
- Python 3.12+
- 无外部库依赖（或列出需要的库）

## 使用方法

### 基本用法
```
skills_run(name="skill-name", command="python scripts/main.py <args>")
```

### 参数说明
- `--input`: 输入文件路径
- `--output`: 输出文件路径（可选）

## 脚本说明

| 脚本 | 功能 |
|------|------|
| `scripts/main.py` | 主逻辑脚本 |
| `scripts/helpers.sh` | 辅助工具 |

## 示例

输入：...
输出：...

## 注意事项
- 不要做什么
- 边界情况处理
```

---

## 脚本编写最佳实践

### Python 脚本

```python
#!/usr/bin/env python3
"""脚本功能描述"""
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="脚本功能")
    parser.add_argument("input", help="输入文件")
    parser.add_argument("-o", "--output", help="输出文件", default="-")
    args = parser.parse_args()
    
    # 处理逻辑...
    
    # 输出到 stdout 或文件
    if args.output == "-":
        print(result)
    else:
        with open(args.output, "w") as f:
            f.write(result)

if __name__ == "__main__":
    main()
```

**要点：**
- 使用 `argparse` 处理参数
- 支持从标准输入/输出
- 使用标准库，避免外部依赖
- 添加清晰的错误信息

### Bash 脚本

```bash
#!/bin/bash
# 脚本功能描述

set -e  # 出错时退出

if [ $# -lt 1 ]; then
    echo "Usage: $0 <input>" >&2
    exit 1
fi

# 处理逻辑...
```

---

## 完整示例：创建代码审查技能

```python
# 1. 创建骨架
skills_create(
    name="code-reviewer",
    description="审查 Python 代码，检查风格和潜在问题",
    instructions="""# Python 代码审查器

## 使用方法
```
skills_run(name="code-reviewer", command="python scripts/review.py <file>")
```

## 脚本说明
- `scripts/review.py`: 主审查脚本，检查语法、风格和常见问题
- `data/rules.json`: 审查规则配置

## 检查项目
1. 语法错误
2. 未使用的导入
3. 函数长度
4. 命名规范
"""
)

# 2. 添加主脚本
skills_write(
    name="code-reviewer",
    file="scripts/review.py",
    content='''#!/usr/bin/env python3
"""Python 代码审查脚本"""
import ast
import sys
from pathlib import Path

def check_syntax(code: str) -> list[str]:
    """检查语法错误"""
    issues = []
    try:
        ast.parse(code)
    except SyntaxError as e:
        issues.append(f"语法错误 (行 {e.lineno}): {e.msg}")
    return issues

def check_imports(tree: ast.AST) -> list[str]:
    """检查未使用的导入"""
    issues = []
    imports = set()
    used_names = set()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports.add(alias.asname or alias.name)
        elif isinstance(node, ast.Name):
            used_names.add(node.id)
    
    unused = imports - used_names
    for name in unused:
        issues.append(f"未使用的导入: {name}")
    
    return issues

def review_file(filepath: str) -> None:
    """审查单个文件"""
    path = Path(filepath)
    if not path.exists():
        print(f"错误: 文件不存在 - {filepath}")
        sys.exit(1)
    
    code = path.read_text()
    print(f"审查文件: {filepath}")
    print("=" * 50)
    
    # 语法检查
    issues = check_syntax(code)
    if issues:
        for issue in issues:
            print(f"❌ {issue}")
        return
    
    print("✓ 语法正确")
    
    # 进一步检查
    tree = ast.parse(code)
    issues = check_imports(tree)
    
    if issues:
        for issue in issues:
            print(f"⚠️  {issue}")
    else:
        print("✓ 导入检查通过")
    
    print("\\n审查完成")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: review.py <file>")
        sys.exit(1)
    review_file(sys.argv[1])
'''
)

# 3. 添加规则配置
skills_write(
    name="code-reviewer",
    file="data/rules.json",
    content='{"max_function_length": 50, "max_line_length": 88}'
)

# 4. 测试
skills_run(name="code-reviewer", command="python scripts/review.py scripts/review.py")
```

---

## 技能管理命令速查

| 工具 | 用途 |
|------|------|
| `skills_list()` | 列出所有技能 |
| `skills_list(name="...")` | 列出技能内文件 |
| `skills_read(name="...")` | 读取 SKILL.md |
| `skills_read(name="...", file="...")` | 读取技能内文件 |
| `skills_create(name="...", ...)` | 创建技能骨架（自动验证） |
| `skills_write(name="...", file="...", content="...")` | 添加/覆盖文件 |
| `skills_run(name="...", command="...")` | 在技能目录执行命令 |

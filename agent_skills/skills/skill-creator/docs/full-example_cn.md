# 完整示例：创建代码审查技能

本文档演示从零创建一个完整技能包的全过程。

## 目标

创建一个 Python 代码审查技能，能够：
- 检查语法错误
- 发现未使用的导入
- 输出审查报告

---

## 第一步：创建技能骨架

```python
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
```

---

## 第二步：添加主脚本

```python
skills_write(
    path="skills/code-reviewer/scripts/review.py",
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
```

---

## 第三步：添加配置文件

```python
skills_write(
    path="skills/code-reviewer/data/rules.json",
    content='{"max_function_length": 50, "max_line_length": 88}'
)
```

---

## 第四步：验证文件结构

```python
skills_ls(path="skills/code-reviewer")
```

期望输出：
```
Contents of 'skills/code-reviewer' (4 items):
  SKILL.md
  data/
  scripts/
```

```python
skills_ls(path="skills/code-reviewer/scripts")
```

期望输出：
```
Contents of 'skills/code-reviewer/scripts' (2 items):
  pyproject.toml  (自动生成)
  review.py
```

---

## 第五步：测试运行

### 测试脚本本身

```python
skills_run(name="code-reviewer", command="python scripts/review.py scripts/review.py")
```

期望输出：
```
审查文件: scripts/review.py
==================================================
✓ 语法正确
✓ 导入检查通过

审查完成
```

### 测试用户文件

```python
skills_run(name="code-reviewer", command="python scripts/review.py /workspace/my_code.py")
```

---

## 最终文件结构

```
code-reviewer/
├── SKILL.md                 # 技能说明文档
├── scripts/
│   ├── review.py            # 主审查脚本
│   └── pyproject.toml       # 依赖配置（自动生成）
└── data/
    └── rules.json           # 审查规则配置
```

---

## 要点总结

| 步骤 | 工具 | 说明 |
|------|------|------|
| 创建骨架 | `skills_create` | 定义名称、描述和初始文档 |
| 添加脚本 | `skills_write` | 路径格式：`skills/<name>/scripts/xxx.py` |
| 添加数据 | `skills_write` | 路径格式：`skills/<name>/data/xxx.json` |
| 验证结构 | `skills_ls` | 确认文件正确创建 |
| 测试运行 | `skills_run` | 验证功能正常 |


# Skill 格式

本文档介绍如何编写和组织 Skill（技能包）。

## 概述

Skill 是一个包含指南、脚本和数据的完整目录结构，教 Agent 如何完成特定任务。

## 目录结构

```
my-skill/
├── SKILL.md          # 入口指南（必需）
├── scripts/          # 可执行脚本
│   ├── main.py
│   └── pyproject.toml  # 依赖配置（自动生成）
├── data/             # 模板和数据文件
│   └── template.txt
├── docs/             # 详细文档（可选）
│   └── advanced.md
└── examples/         # 示例文件
    └── sample.json
```

---

## SKILL.md 格式

SKILL.md 是技能的入口文档，使用 YAML frontmatter + Markdown。

### 基本结构

```markdown
---
name: my-skill
description: 简洁的功能描述（一句话）
---

# 技能名称

## 概述
这个技能做什么，适用于什么场景。

## 使用方法

### 基本用法
\`\`\`
skills_run(name="my-skill", command="python scripts/main.py <args>")
\`\`\`

### 参数说明
- `<input>`：输入文件路径
- `--output`：输出文件路径（可选）

## 脚本说明

| 脚本 | 功能 |
|------|------|
| `scripts/main.py` | 主逻辑脚本 |

## 示例

输入：...
输出：...

## 注意事项
- 注意事项 1
- 注意事项 2
```

### YAML Frontmatter

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | 是 | 技能唯一标识，与目录名一致 |
| `description` | 是 | 简短描述，显示在技能列表中 |

### 命名规则

- 必须以小写字母开头
- 只能包含小写字母、数字和连字符
- 正确：`code-reviewer`, `data-analyzer`, `pdf2image`
- 错误：`Code-Reviewer`, `dataAnalyzer`, `my_tool`

---

## 脚本编写

### Python 脚本模板

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
    result = process(args.input)
    
    if args.output == "-":
        print(result)
    else:
        with open(args.output, "w") as f:
            f.write(result)

if __name__ == "__main__":
    main()
```

### 依赖管理

如果脚本需要第三方库，编辑 `scripts/pyproject.toml`：

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

当 `skills_run` 执行有 `pyproject.toml` 的技能时，会自动使用 `uv` 创建隔离环境。

---

## 创建技能

### 使用 skills_create

```python
skills_create(
    name="my-tool",
    description="Does something useful",
    instructions="# My Tool\n\n## Usage\n..."
)
```

### 添加脚本

```python
skills_write(
    path="skills/my-tool/scripts/main.py",
    content="#!/usr/bin/env python3\nprint('Hello')"
)
```

### 添加数据文件

```python
skills_write(
    path="skills/my-tool/data/template.txt",
    content="Template content here"
)
```

---

## 元技能：skill-creator

系统内置 `skill-creator` 元技能，教 Agent 如何创建新技能。

当使用自定义 skills 目录时，`skill-creator` 会自动复制到该目录。

查看元技能：

```python
skills_read(path="skills/skill-creator/SKILL.md")
```

---

## 项目结构

```
agent_skills/
├── agent_skills/
│   ├── core/
│   │   ├── skill_manager.py  # Skill 发现和管理
│   │   ├── types.py          # 类型定义
│   │   ├── middleware.py     # LangChain Middleware 集成
│   │   ├── docker_runner.py  # Docker 容器管理
│   │   └── tools_factory.py  # LangChain 工具工厂
│   ├── mcp/
│   │   ├── server.py         # MCP Server 入口
│   │   ├── tools.py          # 6 个 skills_* 工具 (MCP)
│   │   └── prompts.py        # Skill Guide Prompt
│   └── skills/               # 内置技能
│       ├── skill-creator/    # 创建技能的元技能
│       ├── gcd-calculator/   # 最大公约数计算
│       ├── pdf/              # PDF 处理
│       └── ...
├── docker_config/
│   └── Dockerfile
├── examples/
│   ├── demo_skills.py        # 本地 Demo
│   ├── demo_with_docker.py   # Docker Demo
│   ├── demo_deepagent.py     # Deep Agent + MCP Demo
│   └── demo_middleware.py    # Deep Agent + Middleware Demo
├── docs/                     # 文档
├── tests/
├── pyproject.toml
└── README.md
```

---

## 最佳实践

### 文档编写

- 开门见山：第一段说清楚技能做什么
- 命令可复制：示例命令可以直接使用
- 参数明确：列出所有参数及其含义
- 有输入输出示例：让用户知道期望结果

### 脚本编写

- 使用 `argparse` 处理参数
- 支持 stdin/stdout（使用 `-` 表示）
- 优先使用标准库，减少依赖
- 添加清晰的错误信息

### 目录组织

- 脚本放在 `scripts/` 目录
- 模板和配置放在 `data/` 目录
- 详细文档放在 `docs/` 目录
- 示例文件放在 `examples/` 目录


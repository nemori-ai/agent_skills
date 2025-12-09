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
│   ├── main.py
│   └── pyproject.toml  (依赖配置)
├── data/             # 模板和数据文件
└── docs/             # 详细文档 (可选)
```

---

## 📖 按场景选择指南

根据你的需求，阅读对应的详细文档：

### 🆕 从零创建新技能

首次创建技能包，需要了解完整流程（5 步创建法）。

```python
skills_read(path="skills/skill-creator/docs/quick-start.md")
```

### 📝 编写/修改 SKILL.md 文档

需要了解 SKILL.md 的结构和模板。

```python
skills_read(path="skills/skill-creator/docs/skillmd-template.md")
```

### 🔧 添加脚本到技能

学习 Python/Bash 脚本编写规范、依赖管理。

```python
skills_read(path="skills/skill-creator/docs/script-guidelines.md")
```

### 🔄 脚本调试失败，需要迭代

创建了替代脚本后如何正确清理旧版本。

```python
skills_read(path="skills/skill-creator/docs/iteration-and-cleanup.md")
```

### 📚 查看完整示例

参考一个完整的技能创建过程（代码审查技能）。

```python
skills_read(path="skills/skill-creator/docs/full-example.md")
```

---

## 命令速查

| 工具 | 用途 | 示例 |
|------|------|------|
| `skills_ls(path="skills")` | 列出所有技能 | 查看可用技能 |
| `skills_ls(path="skills/<name>")` | 列出技能内文件 | 检查文件结构 |
| `skills_read(path="skills/<name>/SKILL.md")` | 读取技能文档 | 学习技能用法 |
| `skills_create(name, description, instructions)` | 创建技能骨架 | 新建技能 |
| `skills_write(path, content)` | 添加/覆盖文件 | 添加脚本 |
| `skills_run(name, command)` | 执行技能命令 | 测试脚本 |
| `skills_bash(command, cwd)` | 执行 shell 命令 | 删除/重命名文件 |

---

## 快速开始

创建一个最简单的技能只需 2 步：

```python
# 1. 创建技能骨架
skills_create(
    name="hello-world",
    description="示例技能",
    instructions="# Hello World\n\n运行 `skills_run(name=\"hello-world\", command=\"python scripts/hello.py\")`"
)

# 2. 添加脚本
skills_write(
    path="skills/hello-world/scripts/hello.py",
    content='print("Hello, World!")'
)

# 3. 测试
skills_run(name="hello-world", command="python scripts/hello.py")
```

需要更详细的指导？阅读 [快速开始指南](docs/quick-start.md)。

"""Prompts for Agent Skills."""

SKILL_GUIDE_PROMPT = """# 技能系统 (Skills System)

## 什么是技能？

技能 (Skill) 是预先封装好的**专业能力模块**，以目录形式存储，包含：
- `SKILL.md`：技能说明书，告诉你这个技能做什么、怎么用
- `scripts/`：可执行脚本（Python、Bash 等）
  - `pyproject.toml`：依赖声明文件（自动生成，用于 uv 管理）
- `data/`：模板、配置或辅助数据

技能让你能够执行超出基础能力的复杂任务，比如：数据分析、代码审查、文档生成、数学计算等。

---

## 何时使用技能？

在以下情况下，你应该检查是否有可用的技能：

1. **用户明确要求**：用户说"用 XX 技能"、"帮我运行 XX"
2. **任务需要专业能力**：如数学计算、代码分析、格式转换、专业知识等
3. **任务有固定流程**：如果某类任务有标准化的处理步骤
4. **需要执行脚本**：任务需要运行 Python/Bash 脚本来完成

**最佳实践**：在开始复杂任务前，先用 `skills_ls(path="skills")` 查看可用技能。

---

## 如何使用技能？

### 1. 发现可用技能
```python
skills_ls(path="skills")  # 列出所有技能（名称 + 简介）
```

### 2. 学习技能用法
```python
skills_read(path="skills/skill-name/SKILL.md")  # 阅读技能说明书
```

### 3. 查看技能内部文件
```python
skills_ls(path="skills/skill-name")                      # 列出技能包含的文件
skills_read(path="skills/skill-name/scripts/xxx.py")     # 查看具体脚本
```

### 4. 执行技能
```python
skills_run(name="skill-name", command="python scripts/xxx.py <args>")
```

**⚠️ 重要**：执行技能前，务必先用 `skills_ls(path="skills/...")` 确认正确的脚本路径，**严禁编造脚本名称**。

---

## 文件系统访问 (File Access)

本系统采用 **路径镜像 (Path Mirroring)** 策略，Docker 容器已挂载宿主机文件系统。

**你拥有对宿主机的直接文件访问权限。**

### 直接操作文件
不需要上传下载，直接使用文件的**绝对路径**：

```python
# 直接读取宿主机文件
skills_read(path="/Users/me/Documents/report.pdf")

# 直接在宿主机目录执行命令
skills_run(name="pdf-tools", command="python scripts/extract.py /Users/me/Documents/report.pdf")

# 结果直接写入宿主机
skills_write(path="/Users/me/Desktop/result.txt", content="Analysis complete")
```

**⚠️ 严禁**：
- ❌ 不要尝试上传文件内容（upload 工具已废弃）
- ❌ 不要把时间浪费在 Base64 编码解码上
- ✅ 总是优先使用绝对路径操作

---

## 依赖管理

技能脚本的依赖通过 `scripts/pyproject.toml` 声明，使用 **uv** 管理：

### 自动生成
当你向 `scripts/` 目录添加 Python 文件时，系统会自动生成 `pyproject.toml`：

```toml
[project]
name = "skill-name-scripts"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.uv]
managed = true
```

### 添加依赖
如果脚本需要第三方库，编辑 `scripts/pyproject.toml` 的 `dependencies`：

```python
skills_read(path="skills/my-skill/scripts/pyproject.toml")  # 先读取
skills_write(path="skills/my-skill/scripts/pyproject.toml", content='''[project]
name = "my-skill-scripts"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["requests>=2.28", "pandas>=2.0"]

[tool.uv]
managed = true
''')
```

### 执行隔离
当 `skills_run` 执行有 `pyproject.toml` 的技能时：
1. 自动创建临时虚拟环境
2. 安装声明的依赖（uv 有缓存，速度很快）
3. 在隔离环境中执行命令
4. 执行完成后自动清理环境

这确保每个技能的依赖互不冲突，且不会影响主机环境。

---

## 如何创建新技能？

**⚠️ 强制要求**：当用户要求创建新技能时，你**必须**先阅读 `skill-creator` 技能：

```python
skills_read(path="skills/skill-creator/SKILL.md")
```

**禁止**：
- ❌ 不要参考其他技能的结构来创建新技能
- ❌ 不要自己猜测技能的目录结构和文件格式
- ❌ 不要跳过阅读 `skill-creator` 直接调用 `skills_create`

**正确流程**：
1. 先执行 `skills_read(path="skills/skill-creator/SKILL.md")` 学习创建规范
2. 按照 `skill-creator` 中的指导创建技能

`skill-creator` 是创建技能的**唯一权威指南**，包含：
- 命名规范
- SKILL.md 编写模板
- 脚本编写最佳实践
- 完整的创建示例

---

## 工具速查（6 个工具）

| 工具 | 用途 |
|------|------|
| `skills_ls(path="skills")` | 列出所有可用技能 |
| `skills_ls(path="skills/X")` | 列出技能 X 的文件 |
| `skills_read(path="skills/X/SKILL.md")` | 阅读技能 X 的说明书 |
| `skills_read(path="skills/X/Y")` | 读取技能 X 中的文件 Y |
| `skills_write(path="skills/X/Y", content="...")` | 向技能 X 写入文件 Y |
| `skills_run(name="X", command="...")` | 在技能 X 目录下执行命令 |
| `skills_create(name, description, instructions)` | 创建新技能（**必须先读 skill-creator**） |
| `skills_bash(command="...")` | 执行通用命令（rm, grep, mkdir 等） |
"""

# 工具参考

Agent Skills 提供 6 个统一前缀的工具，功能原子化，MCP 和 Middleware 接口一致。

## 工具概览

| 工具 | 功能 | 操作范围 |
|------|------|----------|
| `skills_ls` | 列出文件和目录 | 仅 /skills 目录 |
| `skills_read` | 读取文件内容 | 仅 /skills 目录 |
| `skills_write` | 写入文件 | 仅 /skills 目录 |
| `skills_create` | 创建新技能 | 仅 /skills 目录 |
| `skills_run` | 运行技能脚本 | 可通过命令参数访问外部文件 |
| `skills_bash` | 执行 shell 命令 | 仅 /skills 目录 |

> **注意**：管理工具只能操作 `/skills` 目录。如需访问外部文件，使用 `skills_run` 并在命令参数中传递绝对路径。

---

## skills_ls - 列出文件

列出目录内容。此工具只能操作 `/skills` 目录。

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `path` | string | `""` | 要列出的路径（仅限 /skills 内） |

### 路径规则

| 路径 | 说明 |
|------|------|
| `""` | 列出 /skills 根目录 |
| `"skills"` | 列出所有可用技能 |
| `"skills/<name>"` | 列出指定技能的文件 |
| `"./xxx"` 或 `"xxx"` | 相对于 /skills |

### 示例

```python
skills_ls()                              # 列出 /skills 目录
skills_ls(path="skills")                 # 列出所有技能
skills_ls(path="skills/gcd-calculator")  # 列出技能内文件
```

---

## skills_read - 读取文件

读取文本文件内容。此工具只能操作 `/skills` 目录。

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `path` | string | 文件路径（必需，仅限 /skills 内） |

### 路径规则

与 `skills_ls` 相同，只能访问 `/skills` 目录。

### 示例

```python
skills_read(path="skills/gcd-calculator/SKILL.md")       # 读取技能说明
skills_read(path="skills/gcd-calculator/scripts/gcd.py") # 读取脚本
```

---

## skills_write - 写入文件

写入或覆盖文件内容，自动创建父目录。此工具只能操作 `/skills` 目录。

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `path` | string | 文件路径（必需，仅限 /skills 内） |
| `content` | string | 文件内容（必需） |

### 示例

```python
skills_write(path="skills/my-skill/scripts/run.py", content="print('hi')")
skills_write(path="skills/my-skill/data/config.json", content="{...}")
```

---

## skills_create - 创建技能

创建新的技能目录和 SKILL.md 文件。

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | string | 技能名称（小写字母、数字、连字符） |
| `description` | string | 一句话描述 |
| `instructions` | string | SKILL.md 的 Markdown 内容 |

### 命名规则

- 必须以小写字母开头
- 只能包含小写字母、数字和连字符
- 正确：`code-reviewer`, `data-analyzer`, `pdf2image`
- 错误：`Code-Reviewer`, `dataAnalyzer`, `my_tool`

### 示例

```python
skills_create(
    name="my-tool",
    description="Does something useful",
    instructions="# My Tool\n\n## Usage\n运行 `skills_run(name=\"my-tool\", command=\"python scripts/main.py\")`"
)
```

---

## skills_run - 运行技能脚本

在技能目录下执行命令。如果存在 `scripts/pyproject.toml`，会自动使用 `uv` 创建隔离环境。

**这是唯一可以访问外部文件的工具**，通过命令参数传递绝对路径。

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | - | 技能名称（必需） |
| `command` | string | - | 要执行的命令（必需，可包含绝对路径） |
| `timeout` | int | 120 | 超时时间（秒） |

### 执行机制

```
skills_run(name="pdf", command="python scripts/convert.py /Users/xxx/input.pdf")
           │
           ▼
┌─────────────────────────────────────────┐
│ 检查 scripts/pyproject.toml 是否存在    │
└─────────────────────────────────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
 存在           不存在
    │             │
    ▼             ▼
uv sync       直接执行
uv run        命令
```

### 示例

```python
skills_run(name="gcd-calculator", command="python scripts/gcd.py 12 18")
skills_run(name="my-tool", command="bash scripts/setup.sh", timeout=120)
# 处理宿主机文件（需要挂载对应目录）
skills_run(name="pdf", command="python scripts/convert.py /Users/xxx/doc.pdf -o /Users/xxx/doc.md")
```

---

## skills_bash - 执行命令

在 /skills 目录中执行通用 shell 命令。此工具只能操作 `/skills` 目录。

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `command` | string | - | 要执行的命令（必需） |
| `timeout` | int | 60 | 超时时间（秒） |
| `cwd` | string | `""` | 工作目录（仅限 /skills 内） |

### 示例

```python
skills_bash(command="ls -la")                           # 列出 /skills 目录
skills_bash(command="grep -r 'pattern' .", cwd="skills/my-skill")  # 在技能目录搜索
skills_bash(command="rm -rf old-file.txt", cwd="skills/my-skill")  # 删除文件
```

---

## 文件访问工作流

Agent 可以使用绝对路径访问宿主机文件（需要挂载对应目录）：

```
1. 用户请求: "帮我处理 /Users/me/doc.pdf"
2. skills_read("skills/pdf/SKILL.md") → 学习处理方法
3. skills_run("pdf", "python scripts/convert.py /Users/me/doc.pdf -o /Users/me/doc.md")
4. 结果直接生成在宿主机 /Users/me/doc.md
5. Agent 告知用户结果位置
```

---

## 工具权限说明

| 工具 | 操作范围 | 说明 |
|------|----------|------|
| `skills_ls/read/write/create/bash` | 仅 /skills 目录 | 用于技能管理 |
| `skills_run` | 可访问任意挂载路径 | 通过命令参数传递绝对路径 |


# 工具参考

Agent Skills 提供 6 个统一前缀的工具，功能原子化，MCP 和 Middleware 接口一致。

## 工具概览

| 工具 | 功能 | 执行位置 |
|------|------|----------|
| `skills_ls` | 列出文件和目录 | 宿主机 |
| `skills_read` | 读取文件内容 | 宿主机 |
| `skills_write` | 写入文件 | 宿主机 |
| `skills_create` | 创建新技能 | 宿主机 |
| `skills_run` | 运行技能脚本 | Docker 容器 |
| `skills_bash` | 执行 shell 命令 | Docker 容器 |

---

## skills_ls - 列出文件

列出目录内容，支持虚拟路径。

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `path` | string | `""` | 要列出的路径 |

### 路径规则

| 路径 | 说明 |
|------|------|
| `""` 或 `"workspace"` | 列出 workspace 根目录 |
| `"skills"` | 列出所有可用技能 |
| `"skills/<name>"` | 列出指定技能的文件 |
| `"./xxx"` 或 `"xxx"` | 相对于 workspace |
| `"/absolute/path"` | 绝对路径（需挂载） |

### 示例

```python
skills_ls()                              # 列出 workspace
skills_ls(path="skills")                 # 列出所有技能
skills_ls(path="skills/gcd-calculator")  # 列出技能内文件
skills_ls(path="src")                    # 列出 workspace/src
```

---

## skills_read - 读取文件

读取文本文件内容。

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `path` | string | 文件路径（必需） |

### 路径规则

与 `skills_ls` 相同，支持虚拟路径和绝对路径。

### 示例

```python
skills_read(path="skills/gcd-calculator/SKILL.md")       # 读取技能说明
skills_read(path="skills/gcd-calculator/scripts/gcd.py") # 读取脚本
skills_read(path="src/main.py")                          # 读取 workspace 文件
skills_read(path="/Users/me/output.txt")                 # 读取宿主机文件
```

---

## skills_write - 写入文件

写入或覆盖文件内容，自动创建父目录。

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `path` | string | 文件路径（必需） |
| `content` | string | 文件内容（必需） |

### 示例

```python
skills_write(path="output/result.txt", content="Hello World")
skills_write(path="skills/my-skill/scripts/run.py", content="print('hi')")
skills_write(path="/Users/me/output.txt", content="直接写入宿主机")
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

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | - | 技能名称（必需） |
| `command` | string | - | 要执行的命令（必需） |
| `timeout` | int | 120 | 超时时间（秒） |

### 执行机制

```
skills_run(name="pdf", command="python scripts/convert.py input.pdf")
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
# 处理宿主机文件
skills_run(name="pdf-tools", command="python scripts/extract.py /workspace/doc.pdf")
```

---

## skills_bash - 执行命令

在 workspace 中执行通用 shell 命令。

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `command` | string | - | 要执行的命令（必需） |
| `timeout` | int | 60 | 超时时间（秒） |
| `cwd` | string | `""` | 工作目录（支持虚拟路径） |

### 示例

```python
skills_bash(command="ls -la")                           # 列出 workspace
skills_bash(command="grep -r 'pattern' .", timeout=30)  # 搜索
skills_bash(command="mkdir -p output/data")             # 创建目录
skills_bash(command="python main.py", cwd="src")        # 在子目录执行
```

---

## 文件访问工作流

Agent 可以直接使用宿主机路径，无需上传下载：

```
1. 用户请求: "帮我处理 /Users/me/doc.pdf"
2. skills_read("skills/pdf-tools/SKILL.md") → 学习处理方法
3. skills_run("pdf-tools", "python scripts/process.py /workspace/doc.pdf")
4. 结果直接生成在宿主机 (如 /workspace/doc_processed.txt)
5. Agent 读取结果返回给用户
```

---

## 执行位置说明

| 工具 | 执行位置 | 说明 |
|------|----------|------|
| `skills_run` | Docker 容器 | 通过 `docker exec` 执行，支持 `uv` 依赖隔离 |
| `skills_bash` | Docker 容器 | 通过 `docker exec` 执行 |
| `skills_ls/read/write/create` | 宿主机 | 直接操作挂载的文件系统，性能更优 |


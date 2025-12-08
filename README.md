# Agent Skills

一个为 AI Agent 提供的全栈 Skills 系统，支持 **MCP Server** 和 **Python Middleware** 两种集成方式。

## 功能特性

- **统一前缀工具集**: 6 个 `skills_*` 工具，功能原子化，易于理解
- **Docker 隔离执行**: 在容器中运行命令，预装常用工具和库
- **路径镜像 (Path Mirroring)**: 通过挂载宿主机文件系统，Agent 可直接使用绝对路径操作文件，无需上传下载
- **渐进式披露**: Skills 作为 MCP Resource 暴露，预加载元数据，按需读取内容
- **双重集成方式**:
  - **MCP 协议**: 标准 MCP Server 接口，可与任何支持 MCP 的 AI 系统集成（Claude Desktop, Cursor 等）
  - **Python Middleware**: 原生 LangChain 集成，使用官方 `AgentMiddleware` 协议，无需 MCP 协议，更低延迟

## 快速开始

### 使用 Docker（推荐）

使用 **路径镜像** 模式启动，将宿主机根目录（或用户目录）挂载到容器内的相同路径：

```bash
# 构建镜像
docker build -t agent-skills:latest -f docker_config/Dockerfile .

# 运行 MCP Server
# 方式1: 挂载项目目录到 /workspace（推荐）
docker run -i --rm \
  -v /path/to/my-project:/workspace \
  -v ~/.agent-skills/skills:/skills \
  agent-skills:latest

# 方式2: 挂载整个用户目录（完全访问）
docker run -i --rm \
  -v /Users/me:/Users/me \
  -v ~/.agent-skills/skills:/skills \
  agent-skills:latest
```

### Claude Desktop 配置

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-v", "/path/to/my-project:/workspace",
               "-v", "~/.agent-skills/skills:/skills",
               "agent-skills:latest"]
    }
  }
}
```

> **注意**: `/skills` 目录需要读写权限，以便 Agent 可以创建和修改技能。

### 本地开发

```bash
# 安装依赖
uv sync

# 启动 MCP Server
uv run agent-skills-server
```

## 示例 Demo

提供四个示例来演示不同场景：

### 1. 本地 Demo（开发测试）

```bash
# 安装 demo 依赖
uv sync --extra demo

# 运行
python examples/demo_skills.py
```

### 2. Docker Demo（生产环境）

```bash
# 安装 demo 依赖
uv sync --extra demo

# 构建 Docker 镜像
docker build -t agent-skills:latest -f docker_config/Dockerfile .

# 运行
python examples/demo_with_docker.py --workspace /path/to/your/project
```

### 3. Deep Agent + MCP Demo

结合 LangChain Deep Agent + MCP Client 实现任务规划、子代理和网络搜索：

```bash
# 安装 deepagent 依赖
uv sync --extra deepagent

# 构建 Docker 镜像
docker build -t agent-skills:latest -f docker_config/Dockerfile .

# 运行（需要在 .env 中配置 ANTHROPIC_API_KEY）
python examples/demo_deepagent.py
```

### 4. Deep Agent + Middleware Demo（推荐 ⭐）

使用 **LangChain 原生 Middleware** 替代 MCP 协议，完全符合官方 `AgentMiddleware` 协议：

```bash
# 安装依赖
uv sync --extra deepagent
uv pip install docker  # Middleware 需要 docker 包

# 构建 Docker 镜像
docker build -t agent-skills:latest -f docker_config/Dockerfile .

# 运行
python examples/demo_middleware.py
```

**Middleware vs MCP 对比：**

| 特性 | MCP (demo_deepagent.py) | Middleware (demo_middleware.py) |
|------|------------------------|--------------------------------|
| 协议 | JSON-RPC over stdio | LangChain AgentMiddleware |
| 延迟 | 较高（进程间通信） | 较低（直接 docker exec） |
| 依赖 | langchain-mcp-adapters | docker (Python SDK) |
| 适用场景 | Claude Desktop, Cursor | LangChain/LangGraph 应用 |

**Deep Agent 特性（两种集成方式都支持）：**
- 🧠 自动任务规划（`write_todos`）
- 📂 共享文件系统（Deep Agent 和 Skills 使用同一 workspace）
- 🔍 网络搜索（需要 TAVILY_API_KEY）
- 🤖 子代理支持（复杂任务自动拆分）

**环境变量（.env）：**
```
ANTHROPIC_API_KEY=your-anthropic-api-key
TAVILY_API_KEY=your-tavily-api-key  # 可选，用于网络搜索
```

## 工具列表（6 个）

所有工具都以 `skills_` 前缀开头，功能原子化（MCP 和 Middleware 接口一致）：

### skills_bash - 执行命令

```python
skills_bash(command="ls -la")
skills_bash(command="grep -r 'pattern' .", timeout=30)
skills_bash(command="mkdir -p output/data")
```

### skills_ls - 列出文件

```python
skills_ls()                           # 列出 workspace
skills_ls(path="skills")              # 列出所有 skills
skills_ls(path="skills/gcd-calculator")  # 列出 skill 内文件
```

### skills_read - 读取文件

```python
skills_read(path="skills/gcd-calculator/SKILL.md")  # 读取 skill 说明
skills_read(path="skills/gcd-calculator/scripts/gcd.py")  # 读取脚本
skills_read(path="/Users/me/output.txt")  # 直接读取宿主机文件
```

### skills_write - 写入文件

```python
skills_write(path="/Users/me/output.txt", content="Hello World")
skills_write(path="skills/my-skill/scripts/run.py", content="print('hi')")
```

### skills_create - 创建 Skill

```python
skills_create(
    name="my-tool",
    description="Does something useful",
    instructions="# My Tool\n\n## Usage\n..."
)
```

### skills_run - 运行 Skill 脚本

```python
skills_run(name="gcd-calculator", command="python scripts/gcd.py 12 18")
skills_run(name="my-tool", command="bash scripts/setup.sh", timeout=120)
# 直接处理宿主机文件
skills_run(name="pdf-tools", command="python scripts/extract.py /Users/me/doc.pdf")
```

## 文件访问工作流

无需上传下载，Agent 直接使用宿主机绝对路径：

```
1. 用户请求: "帮我处理 /Users/me/doc.pdf"
2. skills_read("skills/pdf-tools/SKILL.md") → 学习处理方法
3. skills_run("pdf-tools", "python scripts/process.py /Users/me/doc.pdf")
4. 结果直接生成在宿主机 (如 /Users/me/doc_processed.txt)
5. Agent 读取结果返回给用户
```

## Python Middleware 集成（LangChain 原生）

对于 LangChain/LangGraph 应用，使用 `DockerSkillsMiddleware` 直接集成，完全符合 [LangChain AgentMiddleware 协议](https://reference.langchain.com/python/langchain/middleware/)：

### 推荐方式：使用 `get_middlewares()`

```python
from agent_skills.core.middleware import DockerSkillsMiddleware
from deepagents import create_deep_agent

# 初始化 Middleware 工厂
middleware_factory = DockerSkillsMiddleware(
    workspace_dir="/path/to/workspace",
    skills_dir="/path/to/skills",
)

# 获取所有 LangChain 原生 middleware
# 返回 3 个 middleware：
#   1. @before_agent - 启动 Docker 容器
#   2. @dynamic_prompt - 动态注入技能系统提示词
#   3. @before_model(tools=[...]) - 注入 skills_* 工具
lc_middlewares = middleware_factory.get_middlewares()

# 创建 Agent - 工具和提示词通过 middleware 自动注入
agent = create_deep_agent(
    tools=other_tools,  # 只需传入非技能工具（如 internet_search）
    system_prompt="You are a helpful assistant.",  # 基础提示词
    middleware=lc_middlewares,  # 技能系统通过 middleware 注入
)
```

### 使用的 LangChain 官方装饰器

| 装饰器 | 用途 | 说明 |
|--------|------|------|
| `@before_agent` | 生命周期管理 | 在 Agent 执行前启动 Docker 容器（幂等） |
| `@dynamic_prompt` | 动态提示词注入 | 每次模型调用前注入技能指南 + 可用技能列表 |
| `@before_model(tools=[...])` | 工具注入 | 注入 6 个 `skills_*` 工具 |

### 备选方式：手动获取工具和提示词

如果需要更细粒度的控制，也可以手动获取：

```python
from agent_skills.core.middleware import DockerSkillsMiddleware
from deepagents import create_deep_agent

middleware = DockerSkillsMiddleware(
    workspace_dir="/path/to/workspace",
    skills_dir="/path/to/skills",
)

# 手动获取工具
tools = middleware.get_tools()

# 手动获取技能提示词
skills_prompt = middleware.get_prompt()

# 手动组合
agent = create_deep_agent(
    tools=tools + other_tools,
    system_prompt=f"You are a helpful assistant.\n\n{skills_prompt}",
)
```

### Middleware 提供的方法

| 方法 | 说明 |
|------|------|
| `get_middlewares()` | 返回 LangChain 原生 middleware 列表（推荐）|
| `get_tools()` | 返回 6 个 `skills_*` LangChain 工具 |
| `get_prompt()` | 返回完整技能提示词（自动发现可用技能） |
| `process(state)` | 运行时注入提示词到 Agent State（Legacy） |

### 执行位置

| 工具 | 执行位置 | 说明 |
|------|----------|------|
| `skills_run` | Docker 容器 | 通过 `docker exec` 执行，支持 `uv` 依赖隔离 |
| `skills_bash` | Docker 容器 | 通过 `docker exec` 执行 |
| `skills_ls/read/write/create` | 宿主机 | 直接操作挂载的文件系统，性能更优 |

## MCP Resources - 技能自动暴露

Skills 作为 MCP Resource **自动暴露**给 Agent：

```
启动时自动获取:
┌─────────────────────────────────────────────────────────────┐
│  list_resources() 返回:                                     │
│                                                             │
│  skill://skill-creator                                      │
│    description: 用于创建新技能的元技能                       │
│                                                             │
│  skill://gcd-calculator                                     │
│    description: 计算最大公约数                               │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
                              ↓ Agent 判断需要时
┌─────────────────────────────────────────────────────────────┐
│  read_resource("skill://skill-creator")                     │
│  → 返回完整 SKILL.md 内容                                   │
└─────────────────────────────────────────────────────────────┘
```

## Skill 格式

Skills 遵循 Claude 官方规范，使用 YAML frontmatter + Markdown：

```markdown
---
name: my-skill
description: What this skill does and when to use it
---

# My Skill

## Overview
[What this skill does]

## Instructions
[How to use this skill]

## Examples
[Concrete examples]
```

## Docker 环境

预装的工具和库：

**系统工具：**
- git, curl, jq
- poppler-utils, qpdf (PDF)
- imagemagick (图像)
- ripgrep (搜索)
- Node.js 22.x

**Python 库：**
- pypdf, pdfplumber (PDF)
- pandas (数据处理)
- pillow (图像)
- requests, httpx (HTTP)
- pyyaml

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SKILLS_WORKSPACE` | `/workspace` | 工作目录 |
| `SKILLS_DIR` | `/skills` | Skills 目录（volume 挂载） |

## 开发

```bash
# 安装依赖
uv sync

# 运行测试
uv run pytest tests/ -v

# 构建 Docker 镜像
docker build -t agent-skills:latest -f docker_config/Dockerfile .
```

## 项目结构

```
agent_skills/
├── agent_skills/
│   ├── core/
│   │   ├── skill_manager.py  # Skill 发现和管理
│   │   ├── types.py          # 类型定义
│   │   ├── middleware.py     # LangChain Middleware 集成（原生协议）
│   │   ├── docker_runner.py  # Docker 容器管理
│   │   └── tools_factory.py  # LangChain 工具工厂
│   ├── mcp/
│   │   ├── server.py         # MCP Server 入口
│   │   ├── tools.py          # 6 个 skills_* 工具 (MCP)
│   │   └── prompts.py        # Skill Guide Prompt
│   └── skills/               # 内置 skills
├── docker_config/
│   └── Dockerfile
├── examples/
│   ├── demo_skills.py        # 本地 Demo
│   ├── demo_with_docker.py   # Docker Demo
│   ├── demo_deepagent.py     # Deep Agent + MCP Demo
│   └── demo_middleware.py    # Deep Agent + Middleware Demo ⭐
├── tests/
├── pyproject.toml
└── README.md
```

## License

Apache 2.0

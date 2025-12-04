# Agent Skills

一个为 AI Agent 提供的全栈 Skills 系统，通过 MCP Server 暴露精简的工具接口。

## 功能特性

- **统一前缀工具集**: 6 个 `skills_*` 工具，功能原子化，易于理解
- **Docker 隔离执行**: 在容器中运行命令，预装常用工具和库
- **路径镜像 (Path Mirroring)**: 通过挂载宿主机文件系统，Agent 可直接使用绝对路径操作文件，无需上传下载
- **渐进式披露**: Skills 作为 MCP Resource 暴露，预加载元数据，按需读取内容
- **MCP 协议**: 标准 MCP Server 接口，可与任何支持 MCP 的 AI 系统集成

## 快速开始

### 使用 Docker（推荐）

使用 **路径镜像** 模式启动，将宿主机根目录（或用户目录）挂载到容器内的相同路径：

```bash
# 构建镜像
docker build -t agent-skills:latest -f docker/Dockerfile .

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

提供三个示例来演示不同场景：

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
docker build -t agent-skills:latest -f docker/Dockerfile .

# 运行
python examples/demo_with_docker.py --workspace /path/to/your/project
```

### 3. Deep Agent Demo（高级功能）

结合 LangChain Deep Agent 实现任务规划、子代理和网络搜索：

```bash
# 安装 deepagent 依赖
uv sync --extra deepagent

# 构建 Docker 镜像
docker build -t agent-skills:latest -f docker/Dockerfile .

# 运行（需要在 .env 中配置 ANTHROPIC_API_KEY）
python examples/demo_deepagent.py --workspace /path/to/your/project
```

**Deep Agent 特性：**
- 🧠 自动任务规划（`write_todos`）
- 📂 共享文件系统（Deep Agent 和 Skills MCP 使用同一 workspace）
- 🔍 网络搜索（需要 TAVILY_API_KEY）
- 🤖 子代理支持（复杂任务自动拆分）

**环境变量（.env）：**
```
ANTHROPIC_API_KEY=your-anthropic-api-key
TAVILY_API_KEY=your-tavily-api-key  # 可选，用于网络搜索
```

## MCP 工具列表（6 个）

所有工具都以 `skills_` 前缀开头，功能原子化：

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
docker build -t agent-skills:latest -f docker/Dockerfile .
```

## 项目结构

```
agent_skills/
├── agent_skills/
│   ├── core/
│   │   ├── skill_manager.py  # Skill 发现和管理
│   │   └── types.py          # 类型定义
│   ├── mcp/
│   │   ├── server.py         # MCP Server 入口
│   │   ├── tools.py          # 6 个 skills_* 工具
│   │   └── prompts.py        # Skill Guide Prompt
│   └── skills/               # 内置 skills
├── docker/
│   ├── Dockerfile
│   └── .dockerignore
├── tests/
├── pyproject.toml
└── README.md
```

## License

Apache 2.0

# MCP 集成指南

本文档介绍如何通过 MCP (Model Context Protocol) 协议集成 Agent Skills。

## 概述

Agent Skills 提供标准的 MCP Server 接口，可与任何支持 MCP 的 AI 系统集成：
- **Cursor** - AI 编程助手
- **Claude Desktop** - Anthropic 官方桌面客户端
- 其他 MCP 兼容客户端

---

## 快速开始

### 方式 A：本地运行（推荐开发时使用）

无需 Docker，直接使用 `uv` 运行：

```bash
# 安装依赖
uv sync

# 启动 MCP Server
uv run agent-skills-server
```

### 方式 B：Docker 运行（推荐生产环境）

```bash
# 构建镜像
docker build -t agent-skills:latest -f docker_config/Dockerfile .

# 运行 MCP Server
docker run -i --rm \
  -v ~/.agent-skills/skills:/skills \
  agent-skills:latest
```

---

## Cursor 配置

Cursor 通过 `~/.cursor/mcp.json` 配置 MCP 服务器。

### 配置文件位置

| 系统 | 路径 |
|------|------|
| macOS | `~/.cursor/mcp.json` |
| Windows | `%USERPROFILE%\.cursor\mcp.json` |
| Linux | `~/.cursor/mcp.json` |

### 配置示例 1：本地运行（最简单）

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/agent_skills",
        "agent-skills-server"
      ]
    }
  }
}
```

**说明**：
- 使用 `uv run` 直接启动 MCP Server
- 无需 Docker，适合开发调试
- Skills 目录使用项目内置的 `agent_skills/skills/`

### 配置示例 2：本地运行 + 自定义 workspace

如果需要 skills 处理外部文件（如 PDF 转换），添加 `SKILLS_WORKSPACE` 环境变量：

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/agent_skills",
        "agent-skills-server"
      ],
      "env": {
        "SKILLS_WORKSPACE": "/path/to/your/project"
      }
    }
  }
}
```

### 配置示例 3：Docker 运行

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "~/.agent-skills/skills:/skills",
        "-v", "/path/to/project:/workspace",
        "agent-skills:latest"
      ]
    }
  }
}
```

### 配置后生效

1. 保存 `mcp.json` 文件
2. **完全重启 Cursor**（Cmd+Q / Alt+F4）
3. 在 Agent 模式中验证 `skills_*` 工具是否可用

---

## Claude Desktop 配置

Claude Desktop 通过 `claude_desktop_config.json` 配置 MCP。

### 配置文件位置

| 系统 | 路径 |
|------|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

### 配置示例 1：只挂载技能目录

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-v", "~/.agent-skills/skills:/skills",
               "agent-skills:latest"]
    }
  }
}
```

### 配置示例 2：同时挂载项目目录

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

### Windows 路径示例

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-v", "C:\\Users\\me\\project:/workspace",
               "-v", "C:\\Users\\me\\.agent-skills\\skills:/skills",
               "agent-skills:latest"]
    }
  }
}
```

---

## 为什么使用 Docker？

### 1. 隔离的执行环境

Skills 脚本可能需要各种依赖（如 `pdf2image`、`pytesseract`），Docker 容器预装了这些工具：

```
Docker 容器内预装：
├── Python 3.12 + uv
├── poppler-utils (PDF 处理)
├── tesseract-ocr (OCR)
├── Node.js 20 (JavaScript 工具)
└── 常用 Python 库
```

### 2. 安全性

- Skills 脚本在容器内执行，不会影响宿主机
- 只有挂载的目录可被访问
- 容器使用后自动销毁（`--rm`）

### 3. 一致性

- 无论在什么系统上运行，环境都相同
- 避免"在我机器上可以运行"的问题

### 4. 何时不需要 Docker

- **开发调试时**：使用 `uv run` 更快
- **只使用纯计算技能**：如 `gcd-calculator`、`prime-list-generator`
- **Agent 已有文件系统后端**：如 DeepAgent 的 FilesystemMiddleware

---

## 为什么需要 Workspace 挂载？

### 场景分析

| 场景 | 是否需要 Workspace | 原因 |
|------|-------------------|------|
| 使用 `gcd-calculator` 计算最大公约数 | ❌ 不需要 | 纯计算，无文件操作 |
| 使用 `pdf` 技能转换 PDF | ✅ 需要 | 需要访问用户的 PDF 文件 |
| 创建新技能 | ❌ 不需要 | 技能写入 `/skills` 目录 |
| 在技能中生成报告到用户目录 | ✅ 需要 | 输出文件到 `/workspace` |

### Workspace 的作用

```
宿主机                          Docker 容器
┌────────────────────┐         ┌────────────────────┐
│ ~/my-project/      │ ──────► │ /workspace/        │
│   ├── report.pdf   │   -v    │   ├── report.pdf   │
│   └── data/        │         │   └── data/        │
└────────────────────┘         └────────────────────┘

# skills_run 可以处理用户文件
skills_run(name="pdf", command="python scripts/convert.py /workspace/report.pdf")
```

### 不挂载 Workspace 时

- `skills_*` 工具默认操作 `/skills` 目录
- 无法访问用户项目文件
- 适合纯技能管理场景

---

## MCP Resources - 渐进式披露

Skills 作为 MCP Resource 自动暴露给 Agent，实现渐进式披露：

```
启动时自动获取（元数据）:
┌─────────────────────────────────────────────────────────────┐
│  list_resources() 返回:                                     │
│                                                             │
│  skill://skill-creator                                      │
│    description: 用于创建新技能的元技能                       │
│                                                             │
│  skill://gcd-calculator                                     │
│    description: 计算最大公约数                               │
│                                                             │
│  skill://pdf                                                │
│    description: PDF 处理技能                                │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ Agent 判断需要时
┌─────────────────────────────────────────────────────────────┐
│  read_resource("skill://skill-creator")                     │
│  → 返回完整 SKILL.md 内容                                   │
└─────────────────────────────────────────────────────────────┘
```

**优势：**
- 启动时只加载技能名称和描述（轻量）
- Agent 按需读取完整内容（节省 token）
- 自动发现新添加的技能

---

## MCP Prompt

系统提供一个内置 Prompt，包含完整的技能系统使用指南：

```python
# MCP 客户端可以获取
get_prompt("skill_guide")
```

返回约 200 行的详细指南，包括：
- 什么是技能
- 何时使用技能
- 如何使用技能（4 步流程）
- 文件系统访问规则
- 6 个工具速查表

---

## 命令行参数

```bash
agent-skills-server [OPTIONS]

选项：
  --skills-dir, -s PATH    额外的技能目录（可多次指定）
  --transport, -t TYPE     传输协议：stdio（默认）或 sse
  --quiet, -q              静默模式，不输出日志
```

### 示例

```bash
# 使用 SSE 传输
uv run agent-skills-server --transport sse

# 添加额外技能目录
uv run agent-skills-server --skills-dir /path/to/custom-skills

# 静默模式
uv run agent-skills-server --quiet
```

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SKILLS_DIR` | `/skills` | 技能目录（必需） |
| `SKILLS_WORKSPACE` | `/workspace` | 工作目录（可选，目录不存在则不启用） |

**设计理念**：`SKILLS_WORKSPACE` 是可选的。如果不配置：
- Skills 工具只操作技能目录
- 适合 Agent 已有自己文件系统后端的场景
- 减少不必要的目录挂载

---

## 常见问题

### Q: Cursor 重启后 skills 工具不可用？

**A**: 检查以下几点：
1. `mcp.json` 语法是否正确（JSON 格式）
2. 路径是否使用绝对路径
3. 使用 Cmd+Q（macOS）或 Alt+F4（Windows）完全退出 Cursor，而不是关闭窗口

### Q: Docker 容器启动失败？

**A**: 
1. 确保 Docker Desktop 正在运行
2. 确保镜像已构建：`docker images agent-skills:latest`
3. 检查挂载路径是否存在

### Q: skills_run 无法访问我的文件？

**A**: 需要挂载 workspace：
- Docker 方式：添加 `-v /your/project:/workspace`
- 本地方式：设置 `SKILLS_WORKSPACE` 环境变量

---

## 与 Middleware 方式对比

| 特性 | MCP | Middleware |
|------|-----|------------|
| 协议 | JSON-RPC over stdio | Python 原生调用 |
| 延迟 | 较高（进程间通信） | 较低（直接调用） |
| 适用场景 | Claude Desktop, Cursor | LangChain/LangGraph 应用 |
| 依赖 | mcp, fastmcp | docker (Python SDK) |
| 配置复杂度 | JSON 配置文件 | Python 代码 |

如果你在开发 LangChain 应用，建议使用 [Middleware 集成](middleware-integration.md)。

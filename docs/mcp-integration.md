# MCP 集成指南

本文档介绍如何通过 MCP (Model Context Protocol) 协议集成 Agent Skills。

## 概述

Agent Skills 提供标准的 MCP Server 接口，可与任何支持 MCP 的 AI 系统集成：
- Claude Desktop
- Cursor
- 其他 MCP 兼容客户端

## 快速启动

### Docker 方式（推荐）

```bash
# 构建镜像
docker build -t agent-skills:latest -f docker_config/Dockerfile .

# 运行 MCP Server
docker run -i --rm \
  -v /path/to/my-project:/workspace \
  -v ~/.agent-skills/skills:/skills \
  agent-skills:latest
```

### 本地方式

```bash
# 安装依赖
uv sync

# 启动 MCP Server
uv run agent-skills-server
```

---

## Claude Desktop 配置

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`:

**只挂载技能目录（推荐）：**

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

**同时挂载项目和技能目录：**

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

**Windows 路径示例：**

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-v", "C:\\Users\\me\\.agent-skills\\skills:/skills",
               "agent-skills:latest"]
    }
  }
}
```

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

## 目录挂载

### 方式 1：只挂载技能目录（推荐，当 Agent 有自己的文件系统时）

```bash
docker run -i --rm \
  -v ~/.agent-skills/skills:/skills \
  agent-skills:latest
```

- `/skills`：技能目录，Agent 可创建和修改技能
- **无 `/workspace`**：skills_* 工具只操作技能目录

适用场景：Agent 已有自己的文件系统后端（如 DeepAgent 的 FilesystemMiddleware）。

### 方式 2：同时挂载项目和技能目录

```bash
docker run -i --rm \
  -v /path/to/my-project:/workspace \
  -v ~/.agent-skills/skills:/skills \
  agent-skills:latest
```

- `/workspace`：用户项目目录，Agent 可读写
- `/skills`：技能目录，Agent 可创建和修改技能

适用场景：需要 skills_* 工具同时操作项目文件和技能。

### 方式 3：挂载用户目录（完全访问）

```bash
docker run -i --rm \
  -v /Users/me:/Users/me \
  -v ~/.agent-skills/skills:/skills \
  agent-skills:latest
```

Agent 可以直接使用绝对路径访问用户目录下的任何文件。

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
| `SKILLS_WORKSPACE` | `/workspace` | 工作目录（可选，如果目录不存在则不启用） |

**注意**：`SKILLS_WORKSPACE` 现在是可选的。如果 `/workspace` 目录不存在（未挂载），skills_* 工具会以 `/skills` 作为默认根目录。

---

## 与 Middleware 方式对比

| 特性 | MCP | Middleware |
|------|-----|------------|
| 协议 | JSON-RPC over stdio | Python 原生调用 |
| 延迟 | 较高（进程间通信） | 较低（直接 docker exec） |
| 适用场景 | Claude Desktop, Cursor | LangChain/LangGraph 应用 |
| 依赖 | mcp, fastmcp | docker (Python SDK) |

如果你在开发 LangChain 应用，建议使用 [Middleware 集成](middleware-integration.md)。


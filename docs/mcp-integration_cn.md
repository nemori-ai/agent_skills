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

### 配置示例 2：Docker 运行（推荐）

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "~/.agent-skills/skills:/skills",
        "-v", "/Users:/Users",
        "agent-skills:latest"
      ]
    }
  }
}
```

两个挂载的作用：
- `~/.agent-skills/skills:/skills` - skills 目录（必需）
- `/Users:/Users` - 宿主机文件访问（可选，用于脚本读写外部文件）

> 💡 Linux 系统请将 `/Users:/Users` 改为 `/home:/home`

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

### 配置示例 1：只挂载技能目录（纯技能管理）

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

### 配置示例 2：挂载宿主机目录（脚本可访问外部文件）

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-v", "~/.agent-skills/skills:/skills",
               "-v", "/Users:/Users",
               "agent-skills:latest"]
    }
  }
}
```

两个挂载的作用：
- `~/.agent-skills/skills:/skills` - skills 目录（必需）
- `/Users:/Users` - 宿主机文件访问（可选，用于脚本读写外部文件）

### Windows 路径示例

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-v", "C:\\Users\\me\\.agent-skills\\skills:/skills",
               "-v", "C:\\Users:/Users",
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

## 为什么需要宿主机目录挂载？

### 场景分析

| 场景 | 是否需要挂载宿主机目录 | 原因 |
|------|----------------------|------|
| 使用 `gcd-calculator` 计算最大公约数 | ❌ 不需要 | 纯计算，无文件操作 |
| 使用 `pdf` 技能转换 PDF | ✅ 需要 | 需要访问用户的 PDF 文件 |
| 创建新技能 | ❌ 不需要 | 技能写入 `/skills` 目录 |
| 在技能中生成报告到用户目录 | ✅ 需要 | 输出文件到用户指定路径 |

### 宿主机挂载的作用

```
宿主机                          Docker 容器
┌────────────────────┐         ┌────────────────────┐
│ /Users/xxx/        │ ──────► │ /Users/xxx/        │
│   ├── Desktop/     │   -v    │   ├── Desktop/     │
│   │   └── doc.pdf  │         │   │   └── doc.pdf  │
│   └── Documents/   │         │   └── Documents/   │
└────────────────────┘         └────────────────────┘

# skills_run 使用绝对路径访问用户文件
skills_run(name="pdf", command="python scripts/convert.py /Users/xxx/Desktop/doc.pdf -o /Users/xxx/Desktop/doc.md")
```

### 不挂载宿主机目录时

- 管理工具（`skills_ls`, `skills_read` 等）只能操作 `/skills` 目录
- `skills_run` 脚本无法访问外部文件
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
| `DISABLE_BUILTIN_SKILLS` | `false` | 禁用内置技能加载 |

### DISABLE_BUILTIN_SKILLS 详解

Docker 镜像内置了多个示例技能（gcd-calculator, pdf, coprime-checker 等）。设置此变量可以控制是否加载这些内置技能：

| 设置 | 内置技能（gcd-calculator, pdf 等） | skill-creator 元技能 |
|-----|----------------------------------|---------------------|
| 不设置（默认） | ✅ 显示在 resources 列表中 | ✅ 自动复制到用户 /skills |
| `true` | ❌ 不显示 | ✅ 仍然自动复制到用户 /skills |

**使用场景**：
- 希望有一个干净的 skills 目录，只包含自己创建的技能
- 但仍然需要 `skill-creator` 来指导创建新技能

**配置示例**：

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
               "-e", "DISABLE_BUILTIN_SKILLS=true",
               "-v", "~/.agent-skills/skills:/skills",
               "-v", "/Users:/Users",
               "agent-skills:latest"]
    }
  }
}
```

### 设计理念

- 管理工具（`skills_ls`, `skills_read` 等）只操作 `/skills` 目录
- 外部文件访问通过 `skills_run` 的命令参数和宿主机目录挂载实现

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

**A**: 需要挂载宿主机目录：
- macOS：添加 `-v /Users:/Users`
- Linux：添加 `-v /home:/home`
- 然后在命令中使用绝对路径，如 `skills_run(name="pdf", command="python scripts/convert.py /Users/xxx/file.pdf")`

### Q: Agent 看不到新添加或删除的技能？

**A**: MCP Server 在启动时加载技能列表。当你添加或删除技能后，需要重启 MCP 才能让 Agent 看到变化：

- **Cursor**：完全重启 Cursor（macOS 使用 Cmd+Q / Windows 使用 Alt+F4），然后重新打开
- **Claude Desktop**：关闭并重新打开 Claude Desktop 应用

> 💡 **提示**：修改已有技能的内容（如编辑 SKILL.md 或脚本）通常不需要重启，因为技能内容是按需读取的。但新增技能或删除技能需要重启 MCP 来刷新技能列表。

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

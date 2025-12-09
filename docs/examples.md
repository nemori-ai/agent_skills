# 示例 Demo

本项目提供 4 个示例程序，演示不同的集成方式和使用场景。

## 概览

| 示例 | 文件 | 集成方式 | 适用场景 |
|------|------|----------|----------|
| 本地 Demo | `demo_skills.py` | 直接调用 | 开发测试 |
| Docker Demo | `demo_with_docker.py` | Docker 执行 | 生产环境 |
| Deep Agent + MCP | `demo_deepagent.py` | MCP Client | Claude Desktop 风格 |
| Deep Agent + Middleware | `demo_middleware.py` | LangChain Middleware | LangChain 应用 |

---

## 1. 本地 Demo（开发测试）

最简单的示例，直接在本地执行技能脚本。

### 安装依赖

```bash
uv sync --extra demo
```

### 运行

```bash
python examples/demo_skills.py
```

### 特点

- 无需 Docker
- 直接调用 `SkillManager`
- 适合开发和调试技能脚本

---

## 2. Docker Demo（生产环境）

在 Docker 容器中执行命令，提供隔离和安全性。

### 安装依赖

```bash
uv sync --extra demo
```

### 构建 Docker 镜像

```bash
docker build -t agent-skills:latest -f docker_config/Dockerfile .
```

### 运行

```bash
python examples/demo_with_docker.py --workspace /path/to/your/project
```

### 特点

- Docker 隔离执行
- 支持自定义 workspace 路径
- 预装常用工具和库

---

## 3. Deep Agent + MCP Demo

结合 LangChain Deep Agent 和 MCP Client，实现完整的智能体功能。

### 安装依赖

```bash
uv sync --extra deepagent
```

### 构建 Docker 镜像

```bash
docker build -t agent-skills:latest -f docker_config/Dockerfile .
```

### 配置环境变量

创建 `.env` 文件：

```
ANTHROPIC_API_KEY=your-anthropic-api-key
TAVILY_API_KEY=your-tavily-api-key  # 可选，用于网络搜索
```

### 运行

```bash
python examples/demo_deepagent.py
```

### 特点

- 通过 MCP 协议连接技能系统
- 支持任务规划（`write_todos`）
- 支持网络搜索（需要 TAVILY_API_KEY）
- 支持子代理（复杂任务自动拆分）

---

## 4. Deep Agent + Middleware Demo（推荐）

使用 LangChain 原生 Middleware 替代 MCP 协议，更低延迟。

### 安装依赖

```bash
uv sync --extra deepagent
uv pip install docker  # Middleware 需要 docker 包
```

### 构建 Docker 镜像

```bash
docker build -t agent-skills:latest -f docker_config/Dockerfile .
```

### 配置环境变量

创建 `.env` 文件：

```
ANTHROPIC_API_KEY=your-anthropic-api-key
TAVILY_API_KEY=your-tavily-api-key  # 可选
```

### 运行

```bash
python examples/demo_middleware.py
```

### 特点

- 使用 `DockerSkillsMiddleware` 原生集成
- 符合 LangChain AgentMiddleware 协议
- 比 MCP 方式延迟更低
- 自动注入工具和提示词

---

## MCP vs Middleware 对比

| 特性 | MCP (demo_deepagent.py) | Middleware (demo_middleware.py) |
|------|------------------------|--------------------------------|
| 协议 | JSON-RPC over stdio | LangChain AgentMiddleware |
| 延迟 | 较高（进程间通信） | 较低（直接 docker exec） |
| 依赖 | langchain-mcp-adapters | docker (Python SDK) |
| 适用场景 | Claude Desktop, Cursor | LangChain/LangGraph 应用 |

---

## Deep Agent 共有特性

两种集成方式都支持以下 Deep Agent 特性：

| 特性 | 说明 |
|------|------|
| 自动任务规划 | 使用 `write_todos` 分解复杂任务 |
| 共享文件系统 | Deep Agent 和 Skills 使用同一 workspace |
| 网络搜索 | 集成 Tavily 搜索（需配置 API Key） |
| 子代理支持 | 复杂任务自动拆分给子代理处理 |

---

## 常见问题

### Docker 镜像构建失败

确保 Docker 已安装并运行：

```bash
docker --version
docker info
```

### API Key 错误

检查 `.env` 文件是否存在且格式正确：

```bash
cat .env
```

### 找不到技能

确保技能目录正确挂载：

```bash
# 检查技能目录
ls -la ~/.agent-skills/skills/
```

### Middleware 连接失败

确保 Docker 容器可以正常启动：

```bash
docker run --rm agent-skills:latest echo "Hello"
```


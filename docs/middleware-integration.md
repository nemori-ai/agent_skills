# Middleware 集成指南

本文档介绍如何通过 LangChain 原生 Middleware 集成 Agent Skills。

## 概述

对于 LangChain/LangGraph 应用，使用 `SkillsMiddleware` 直接集成，完全符合 [LangChain AgentMiddleware 协议](https://reference.langchain.com/python/langchain/middleware/)。

**优势：**
- 无需 MCP 协议，更低延迟
- 原生 Python 调用，调试更方便
- 自动注入工具和提示词

## 安装依赖

```bash
uv sync --extra deepagent
uv pip install docker  # Middleware 需要 docker 包
```

---

## 推荐方式：使用 `get_middlewares()`

```python
from agent_skills.core.middleware import SkillsMiddleware
from deepagents import create_deep_agent

# 初始化 Middleware 工厂
# 只需配置 skills_dir，workspace 由 Agent 自己的文件系统后端管理
middleware_factory = SkillsMiddleware(
    skills_dir="/path/to/skills",
    # workspace_dir 是可选的，当 Agent 已有文件系统后端时不需要
)

# 获取所有 LangChain 原生 middleware
lc_middlewares = middleware_factory.get_middlewares()

# 创建 Agent - 工具和提示词通过 middleware 自动注入
agent = create_deep_agent(
    tools=other_tools,  # 只需传入非技能工具（如 internet_search）
    system_prompt="You are a helpful assistant.",  # 基础提示词
    middleware=lc_middlewares,  # 技能系统通过 middleware 注入
)
```

### 何时需要配置 `workspace_dir`？

`workspace_dir` 在以下两种场景需要配置：

**场景 1：Agent 没有自己的文件系统后端**

```python
# Agent 需要通过 skills_* 工具操作文件
middleware_factory = SkillsMiddleware(
    skills_dir="/path/to/skills",
    workspace_dir="/path/to/workspace",
)
```

**场景 2：skills_run 需要处理外部文件**

即使 Agent 有自己的文件系统后端，如果你需要用技能脚本处理用户文件（如 PDF 转换），也需要配置 `workspace_dir`：

```python
# 用 pdf 技能处理用户的 PDF 文件
middleware_factory = SkillsMiddleware(
    skills_dir="/path/to/skills",
    workspace_dir="/path/to/user/project",  # 包含用户 PDF 的目录
)

# 现在可以：
# skills_run(name="pdf", command="python scripts/convert.py /workspace/report.pdf")
```

**不需要配置的场景：**
- 只使用纯计算技能（如 `gcd-calculator`、`prime-list-generator`）
- Agent 有自己的文件系统，且技能不需要处理外部文件

---

## Middleware 组成

`get_middlewares()` 返回 3 个 LangChain 原生 middleware：

| 序号 | 类型 | 装饰器 | 功能 |
|------|------|--------|------|
| 1 | 生命周期 | `@before_agent` | 在 Agent 执行前启动 Docker 容器（幂等） |
| 2 | 提示词 | `@dynamic_prompt` | 每次模型调用前注入技能指南 + 可用技能列表 |
| 3 | 工具 | `@before_model(tools=[...])` | 注入 6 个 `skills_*` 工具 |

### 执行时序

```
用户输入
    │
    ▼
@before_agent: 启动 Docker 容器
    │
    ▼
@dynamic_prompt: 注入技能提示词
    │          ├─ SKILL_GUIDE_PROMPT (~200行)
    │          └─ 当前可用技能列表
    │
    ▼
@before_model: 注入 skills_* 工具
    │
    ▼
LLM 推理
    │
    ▼
工具调用（如需要）
    │
    ▼
返回结果
```

---

## 备选方式：手动获取工具和提示词

如果需要更细粒度的控制：

```python
from agent_skills.core.middleware import SkillsMiddleware
from deepagents import create_deep_agent

middleware = SkillsMiddleware(
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

---

## API 参考

### SkillsMiddleware

```python
SkillsMiddleware(
    skills_dir: str = None,      # 技能目录路径（挂载到 /skills）
    workspace_dir: str = None,   # 可选：工作空间路径（挂载到 /workspace）
)
```

**参数说明：**
- `skills_dir`：技能目录路径。如果为 `None`，使用内置技能目录。挂载到 Docker 容器的 `/skills`。
- `workspace_dir`：可选。配置后挂载到 Docker 容器的 `/workspace`。需要配置的场景：
  1. Agent 没有自己的文件系统后端，需要通过 skills_* 工具操作文件
  2. `skills_run` 需要处理技能目录外的文件（如用 pdf 技能转换用户 PDF）

### 方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `get_middlewares(stop_on_exit=False)` | `List[AgentMiddleware]` | 返回 LangChain 原生 middleware 列表 |
| `get_tools()` | `List[BaseTool]` | 返回 6 个 `skills_*` LangChain 工具 |
| `get_prompt()` | `str` | 返回完整技能提示词（含技能列表） |
| `close(remove_container=False)` | `None` | 停止 Docker 容器 |

### 参数说明

- `stop_on_exit=True`：Agent 执行完毕后自动停止 Docker 容器
- `remove_container=True`：停止时同时删除容器

---

## 执行位置与文件访问

| 工具 | 执行位置 | 说明 |
|------|----------|------|
| `skills_run` | Docker 容器 | 通过 `docker exec` 执行，支持 `uv` 依赖隔离 |
| `skills_bash` | Docker 容器 | 通过 `docker exec` 执行 |
| `skills_ls/read/write/create` | 宿主机 | 直接操作文件系统，性能更优 |

### 文件访问范围

**重要**：Middleware 通过 Docker 提供隔离，skills_* 工具**只能访问挂载的目录**：

```
┌─────────────────────────────────────────────────────────────┐
│  Docker 容器                                                │
│                                                             │
│  /skills    ← 始终挂载（来自 skills_dir）                   │
│  /workspace ← 可选挂载（来自 workspace_dir）                │
│                                                             │
│  ❌ 无法访问其他宿主机目录                                   │
└─────────────────────────────────────────────────────────────┘
```

| 配置 | skills_* 可访问 | 典型用例 |
|------|-----------------|----------|
| 只配置 `skills_dir` | 仅 `/skills` | 纯计算技能，Agent 有自己的文件系统 |
| 配置两者 | `/skills` + `/workspace` | 技能需要处理用户文件（如 PDF 转换） |

**如果需要访问任意文件**：将 `workspace_dir` 设置为用户主目录：

```python
middleware = SkillsMiddleware(
    skills_dir="/path/to/skills",
    workspace_dir="/Users/username",  # 挂载整个用户目录
)
```

---

## 与 MCP 方式对比

| 特性 | Middleware | MCP |
|------|------------|-----|
| 协议 | Python 原生调用 | JSON-RPC over stdio |
| 延迟 | 较低（直接 docker exec） | 较高（进程间通信） |
| 适用场景 | LangChain/LangGraph 应用 | Claude Desktop, Cursor |
| 依赖 | docker (Python SDK) | mcp, fastmcp |

---

## 完整示例

参考 [examples/demo_middleware.py](../examples/demo_middleware.py)：

```python
import asyncio
from pathlib import Path
from agent_skills.core.middleware import SkillsMiddleware
from deepagents import create_deep_agent

async def main():
    # 设置技能目录
    skills = Path("./skills")
    skills.mkdir(exist_ok=True)
    
    # 初始化 Middleware（只需 skills_dir）
    middleware = SkillsMiddleware(
        skills_dir=str(skills),
    )
    
    # 创建 Agent
    agent = create_deep_agent(
        tools=[],  # 可添加其他工具
        system_prompt="You are a helpful assistant.",
        middleware=middleware.get_middlewares(),
    )
    
    # 运行
    result = await agent.ainvoke({
        "messages": [{"role": "user", "content": "列出所有可用技能"}]
    })
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```


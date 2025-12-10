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
middleware_factory = SkillsMiddleware(
    skills_dir="/path/to/skills",
    host_mount="/Users:/Users",  # 可选：挂载宿主机目录，用于脚本访问外部文件
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

### 何时需要配置 `host_mount`？

`host_mount` 用于让 skills_run 脚本访问外部文件：

**场景：skills_run 需要处理外部文件**

```python
# 用 pdf 技能处理用户的 PDF 文件
middleware_factory = SkillsMiddleware(
    skills_dir="/path/to/skills",
    host_mount="/Users:/Users",  # macOS，Linux 使用 "/home:/home"
)

# 现在可以使用绝对路径：
# skills_run(name="pdf", command="python scripts/convert.py /Users/xxx/report.pdf -o /Users/xxx/report.md")
```

**不需要配置的场景：**
- 只使用纯计算技能（如 `gcd-calculator`、`prime-list-generator`）
- Agent 有自己的文件系统后端处理文件读写

### 向后兼容：workspace_dir (deprecated)

旧版本使用 `workspace_dir` 参数，该参数仍然有效但已废弃：

```python
# 不推荐，请使用 host_mount
middleware_factory = SkillsMiddleware(
    skills_dir="/path/to/skills",
    workspace_dir="/path/to/workspace",  # deprecated
)
```

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
    host_mount: str = None,      # 可选：宿主机目录挂载（如 "/Users:/Users"）
    workspace_dir: str = None,   # deprecated，请使用 host_mount
)
```

**参数说明：**
- `skills_dir`：技能目录路径。如果为 `None`，使用内置技能目录。挂载到 Docker 容器的 `/skills`。
- `host_mount`：宿主机目录挂载，格式为 "host_path:container_path"。
  - macOS 示例：`"/Users:/Users"`
  - Linux 示例：`"/home:/home"`
  - 用于让 skills_run 脚本访问外部文件
- `workspace_dir`：(deprecated) 旧版参数，挂载到 `/workspace`。请使用 `host_mount` 替代。

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

### 工具权限划分

| 工具 | 执行位置 | 操作范围 |
|------|----------|----------|
| `skills_ls/read/write/create/bash` | Docker 容器 | 仅 `/skills` 目录 |
| `skills_run` | Docker 容器 | 可通过命令参数访问任意挂载路径 |

### 文件访问范围

**重要**：管理工具（skills_ls, skills_read 等）只能操作 `/skills` 目录。如需访问外部文件，使用 `skills_run` 并通过命令参数传递绝对路径。

```
┌─────────────────────────────────────────────────────────────┐
│  Docker 容器                                                │
│                                                             │
│  /skills    ← 始终挂载（来自 skills_dir）                   │
│  /Users     ← 可选挂载（来自 host_mount="/Users:/Users"）   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

| 配置 | skills_run 可访问 | 典型用例 |
|------|------------------|----------|
| 只配置 `skills_dir` | 仅 `/skills` | 纯计算技能 |
| 配置 `host_mount="/Users:/Users"` | `/skills` + `/Users/*` | 脚本需要处理用户文件 |

**访问外部文件示例**：

```python
middleware = SkillsMiddleware(
    skills_dir="/path/to/skills",
    host_mount="/Users:/Users",  # macOS
)

# skills_run 可以使用绝对路径
# skills_run(name="pdf", command="python scripts/convert.py /Users/xxx/doc.pdf -o /Users/xxx/doc.md")
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

参考 [examples/demo_deepagent_middleware.py](../examples/demo_deepagent_middleware.py)：

```python
import asyncio
from pathlib import Path
from agent_skills.core.middleware import SkillsMiddleware
from deepagents import create_deep_agent

async def main():
    # 设置技能目录
    skills = Path("./skills")
    skills.mkdir(exist_ok=True)
    
    # 初始化 Middleware
    middleware = SkillsMiddleware(
        skills_dir=str(skills),
        host_mount="/Users:/Users",  # 可选：让脚本能访问外部文件
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


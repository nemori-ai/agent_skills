# Middleware Integration Guide

This document explains how to integrate Agent Skills via LangChain native Middleware.

## Overview

For LangChain/LangGraph applications, use `SkillsMiddleware` for direct integration, fully compliant with the [LangChain AgentMiddleware protocol](https://reference.langchain.com/python/langchain/middleware/).

**Advantages:**
- No MCP protocol required, lower latency
- Native Python calls, easier debugging
- Automatic tool and prompt injection

## Install Dependencies

```bash
uv sync --extra deepagent
uv pip install docker  # Middleware requires docker package
```

---

## Recommended: Using `get_middlewares()`

```python
from agent_skills.core.middleware import SkillsMiddleware
from deepagents import create_deep_agent

# Initialize Middleware factory
middleware_factory = SkillsMiddleware(
    skills_dir="/path/to/skills",
    host_mount="/Users:/Users",  # Optional: mount host directory for scripts to access external files
)

# Get all LangChain native middlewares
lc_middlewares = middleware_factory.get_middlewares()

# Create Agent - tools and prompts are injected automatically via middleware
agent = create_deep_agent(
    tools=other_tools,  # Only pass non-skill tools (e.g., internet_search)
    system_prompt="You are a helpful assistant.",  # Base prompt
    middleware=lc_middlewares,  # Skills system injected via middleware
)
```

### When to Configure `host_mount`?

`host_mount` allows skills_run scripts to access external files:

**Scenario: skills_run needs to process external files**

```python
# Use pdf skill to process user's PDF file
middleware_factory = SkillsMiddleware(
    skills_dir="/path/to/skills",
    host_mount="/Users:/Users",  # macOS, use "/home:/home" for Linux
)

# Now you can use absolute paths:
# skills_run(name="pdf", command="python scripts/convert.py /Users/xxx/report.pdf -o /Users/xxx/report.md")
```

**Scenarios where configuration is not needed:**
- Only using pure computation skills (like `gcd-calculator`, `prime-list-generator`)
- Agent has its own filesystem backend for file read/write

### Backward Compatibility: workspace_dir (deprecated)

Older versions use the `workspace_dir` parameter, which still works but is deprecated:

```python
# Not recommended, please use host_mount
middleware_factory = SkillsMiddleware(
    skills_dir="/path/to/skills",
    workspace_dir="/path/to/workspace",  # deprecated
)
```

---

## Middleware Components

`get_middlewares()` returns 3 LangChain native middlewares:

| Order | Type | Decorator | Function |
|-------|------|-----------|----------|
| 1 | Lifecycle | `@before_agent` | Start Docker container before Agent execution (idempotent) |
| 2 | Prompt | `@dynamic_prompt` | Inject skills guide + available skills list before each model call |
| 3 | Tools | `@before_model(tools=[...])` | Inject 6 `skills_*` tools |

### Execution Sequence

```
User Input
    │
    ▼
@before_agent: Start Docker container
    │
    ▼
@dynamic_prompt: Inject skills prompt
    │          ├─ SKILL_GUIDE_PROMPT (~200 lines)
    │          └─ Current available skills list
    │
    ▼
@before_model: Inject skills_* tools
    │
    ▼
LLM Inference
    │
    ▼
Tool Calls (if needed)
    │
    ▼
Return Result
```

---

## Alternative: Manually Get Tools and Prompts

For more fine-grained control:

```python
from agent_skills.core.middleware import SkillsMiddleware
from deepagents import create_deep_agent

middleware = SkillsMiddleware(
    skills_dir="/path/to/skills",
)

# Manually get tools
tools = middleware.get_tools()

# Manually get skills prompt
skills_prompt = middleware.get_prompt()

# Manual combination
agent = create_deep_agent(
    tools=tools + other_tools,
    system_prompt=f"You are a helpful assistant.\n\n{skills_prompt}",
)
```

---

## API Reference

### SkillsMiddleware

```python
SkillsMiddleware(
    skills_dir: str = None,      # Skills directory path (mounted to /skills)
    host_mount: str = None,      # Optional: host directory mount (e.g., "/Users:/Users")
    workspace_dir: str = None,   # deprecated, please use host_mount
)
```

**Parameters:**
- `skills_dir`: Skills directory path. If `None`, uses built-in skills directory. Mounted to Docker container's `/skills`.
- `host_mount`: Host directory mount, format is "host_path:container_path".
  - macOS example: `"/Users:/Users"`
  - Linux example: `"/home:/home"`
  - Used for skills_run scripts to access external files
- `workspace_dir`: (deprecated) Old parameter, mounted to `/workspace`. Please use `host_mount` instead.

### Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get_middlewares(stop_on_exit=False)` | `List[AgentMiddleware]` | Returns list of LangChain native middlewares |
| `get_tools()` | `List[BaseTool]` | Returns 6 `skills_*` LangChain tools |
| `get_prompt()` | `str` | Returns complete skills prompt (with skills list) |
| `close(remove_container=False)` | `None` | Stop Docker container |

### Parameter Notes

- `stop_on_exit=True`: Automatically stop Docker container after Agent execution completes
- `remove_container=True`: Also remove container when stopping

---

## Execution Location and File Access

### Tool Permission Division

| Tool | Execution Location | Scope |
|------|-------------------|-------|
| `skills_ls/read/write/create/bash` | Docker container | `/skills` directory only |
| `skills_run` | Docker container | Can access any mounted path via command arguments |

### File Access Scope

**Important**: Management tools (skills_ls, skills_read, etc.) can only operate on the `/skills` directory. To access external files, use `skills_run` and pass absolute paths via command arguments.

```
┌─────────────────────────────────────────────────────────────┐
│  Docker Container                                           │
│                                                             │
│  /skills    ← Always mounted (from skills_dir)              │
│  /Users     ← Optional mount (from host_mount="/Users:/Users") │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

| Configuration | skills_run Can Access | Typical Use Case |
|---------------|----------------------|------------------|
| Only `skills_dir` configured | `/skills` only | Pure computation skills |
| `host_mount="/Users:/Users"` configured | `/skills` + `/Users/*` | Scripts need to process user files |

**External File Access Example**:

```python
middleware = SkillsMiddleware(
    skills_dir="/path/to/skills",
    host_mount="/Users:/Users",  # macOS
)

# skills_run can use absolute paths
# skills_run(name="pdf", command="python scripts/convert.py /Users/xxx/doc.pdf -o /Users/xxx/doc.md")
```

---

## Comparison with MCP

| Feature | Middleware | MCP |
|---------|------------|-----|
| Protocol | Python native calls | JSON-RPC over stdio |
| Latency | Lower (direct docker exec) | Higher (inter-process communication) |
| Use Cases | LangChain/LangGraph applications | Claude Desktop, Cursor |
| Dependencies | docker (Python SDK) | mcp, fastmcp |

---

## Complete Example

See [examples/demo_deepagent_middleware.py](../examples/demo_deepagent_middleware.py):

```python
import asyncio
from pathlib import Path
from agent_skills.core.middleware import SkillsMiddleware
from deepagents import create_deep_agent

async def main():
    # Set up skills directory
    skills = Path("./skills")
    skills.mkdir(exist_ok=True)
    
    # Initialize Middleware
    middleware = SkillsMiddleware(
        skills_dir=str(skills),
        host_mount="/Users:/Users",  # Optional: allow scripts to access external files
    )
    
    # Create Agent
    agent = create_deep_agent(
        tools=[],  # Can add other tools
        system_prompt="You are a helpful assistant.",
        middleware=middleware.get_middlewares(),
    )
    
    # Run
    result = await agent.ainvoke({
        "messages": [{"role": "user", "content": "List all available skills"}]
    })
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

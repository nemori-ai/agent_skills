# Examples

This project provides 4 example programs demonstrating different integration methods and use cases.

## Overview

| Example | File | Integration Method | Use Case |
|---------|------|-------------------|----------|
| Local Demo | `demo_skills.py` | Direct call | Development testing |
| Docker Demo | `demo_with_docker.py` | Docker execution | Production environment |
| Deep Agent + MCP | `demo_deepagent.py` | MCP Client | Claude Desktop style |
| Deep Agent + Middleware | `demo_middleware.py` | LangChain Middleware | LangChain applications |

---

## 1. Local Demo (Development Testing)

The simplest example, directly executing skill scripts locally.

### Install Dependencies

```bash
uv sync --extra demo
```

### Run

```bash
python examples/demo_skills.py
```

### Features

- No Docker required
- Direct `SkillManager` calls
- Suitable for developing and debugging skill scripts

---

## 2. Docker Demo (Production Environment)

Execute commands in a Docker container, providing isolation and security.

### Install Dependencies

```bash
uv sync --extra demo
```

### Build Docker Image

```bash
docker build -t agent-skills:latest -f docker_config/Dockerfile .
```

### Run

```bash
python examples/demo_with_docker.py --workspace /path/to/your/project
```

### Features

- Docker isolated execution
- Support for custom workspace path
- Pre-installed common tools and libraries

---

## 3. Deep Agent + MCP Demo

Combines LangChain Deep Agent with MCP Client for complete agent functionality.

### Install Dependencies

```bash
uv sync --extra deepagent
```

### Build Docker Image

```bash
docker build -t agent-skills:latest -f docker_config/Dockerfile .
```

### Configure Environment Variables

Create `.env` file:

```
ANTHROPIC_API_KEY=your-anthropic-api-key
TAVILY_API_KEY=your-tavily-api-key  # Optional, for web search
```

### Run

```bash
python examples/demo_deepagent.py
```

### Features

- Connect to skills system via MCP protocol
- Support task planning (`write_todos`)
- Support web search (requires TAVILY_API_KEY)
- Support sub-agents (complex tasks auto-split)

---

## 4. Deep Agent + Middleware Demo (Recommended)

Uses LangChain native Middleware instead of MCP protocol for lower latency.

### Install Dependencies

```bash
uv sync --extra deepagent
uv pip install docker  # Middleware requires docker package
```

### Build Docker Image

```bash
docker build -t agent-skills:latest -f docker_config/Dockerfile .
```

### Configure Environment Variables

Create `.env` file:

```
ANTHROPIC_API_KEY=your-anthropic-api-key
TAVILY_API_KEY=your-tavily-api-key  # Optional
```

### Run

```bash
python examples/demo_middleware.py
```

### Features

- Uses `SkillsMiddleware` for native integration
- Compliant with LangChain AgentMiddleware protocol
- Lower latency than MCP approach
- Automatic tool and prompt injection

---

## MCP vs Middleware Comparison

| Feature | MCP (demo_deepagent.py) | Middleware (demo_middleware.py) |
|---------|------------------------|--------------------------------|
| Protocol | JSON-RPC over stdio | LangChain AgentMiddleware |
| Latency | Higher (inter-process communication) | Lower (direct docker exec) |
| Dependencies | langchain-mcp-adapters | docker (Python SDK) |
| Use Cases | Claude Desktop, Cursor | LangChain/LangGraph applications |

---

## Common Deep Agent Features

Both integration methods support the following Deep Agent features:

| Feature | Description |
|---------|-------------|
| Automatic Task Planning | Use `write_todos` to decompose complex tasks |
| Shared Filesystem | Deep Agent and Skills use the same workspace |
| Web Search | Integrated Tavily search (requires API Key) |
| Sub-agent Support | Complex tasks automatically split to sub-agents |

---

## FAQ

### Docker Image Build Fails

Ensure Docker is installed and running:

```bash
docker --version
docker info
```

### API Key Errors

Check if `.env` file exists and has correct format:

```bash
cat .env
```

### Cannot Find Skills

Ensure skills directory is correctly mounted:

```bash
# Check skills directory
ls -la ~/.agent-skills/skills/
```

### Middleware Connection Fails

Ensure Docker container can start normally:

```bash
docker run --rm agent-skills:latest echo "Hello"
```

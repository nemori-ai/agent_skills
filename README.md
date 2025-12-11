# Agent Skills

**Enable any AI Agent to gain Skills capability with one click, driving Agent self-evolution**

> 📖 [中文文档 (Chinese Documentation)](docs/README_cn.md)

## Vision

We believe AI Agents should have the ability to **self-evolve**—not just execute tasks, but also learn new skills and create new tools.

**Skills** are the core mechanism to realize this vision:
- Agents can learn pre-packaged professional knowledge and scripts at any time
- Agents can create entirely new skills as needed
- Skills exist as independent modules that can be shared and reused

**Agent Skills** enables any AI Agent to gain this capability with one click:

- **MCP Protocol Support**: Compatible with Claude Desktop, Cursor, etc.
- **LangChain Middleware Support**: Native integration into your Agent applications
- **Docker Isolated Execution**: Secure, reliable, and ready to use out of the box
- **Progressive Disclosure**: Lightweight loading, on-demand reading

```
┌─────────────────────────────────────────────────────────────┐
│                      Your AI Agent                          │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ LangChain   │  │ Claude      │  │ Custom      │         │
│  │ Agent       │  │ Desktop     │  │ Agent       │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          │                                  │
│                          ▼                                  │
│              ┌───────────────────────┐                      │
│              │    Agent Skills       │                      │
│              │  ┌─────┐ ┌─────────┐  │                      │
│              │  │ MCP │ │Middleware│ │                      │
│              │  └─────┘ └─────────┘  │                      │
│              └───────────────────────┘                      │
│                          │                                  │
│                          ▼                                  │
│              ┌───────────────────────┐                      │
│              │   Skills Ecosystem    │                      │
│              │  PDF | Code Review    │                      │
│              │  Data Analysis | ...  │                      │
│              └───────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Features

- **Unified Toolset**: 6 `skills_*` tools with atomic functionality, easy to understand
- **Docker Isolated Execution**: Run commands in containers with pre-installed tools and libraries
- **Dual Integration Options**:
  - MCP Protocol: Compatible with Claude Desktop, Cursor, etc.
  - LangChain Middleware: Native Python integration with lower latency
- **Progressive Disclosure**: Skill metadata pre-loaded, full content read on demand
- **Meta-skill Auto-copy**: Automatically get `skill-creator` when using custom skills directory

---

## Built-in Skills

In addition to the core framework capabilities, we provide several carefully designed skills ready to use:

| Skill | Description | Highlights |
|-------|-------------|------------|
| 🛠️ **skill-creator** | Meta-skill that teaches you how to create new skills | Complete creation guide and templates |
| 📄 **pdf** | Comprehensive PDF processing toolkit | Text extraction, table parsing, merge/split, form filling |
| 🌐 **website_design** | Website design system | Monochrome, Bauhaus and other unique style specifications |
| ⬇️ **file-downloader** | File downloader | HTTP/HTTPS support, automatic filename detection |

> 🌟 **We look forward to you creating more interesting skills!** Using the `skill-creator` meta-skill, you can easily package your professional knowledge and tools. If you create useful skills, feel free to contribute to the community.

---

## Quick Start

### 1. Build Docker Image

```bash
docker build -t agent-skills:latest -f docker_config/Dockerfile .
```

### 2. Choose Integration Method

**Option A: Claude Desktop / Cursor (MCP)**

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

The two mounts serve these purposes:
- `~/.agent-skills/skills:/skills` - Skills directory (required), modify to your preferred storage location
- `/Users:/Users` - Host file access (optional, for scripts to read/write external files)

> 💡 **Tip**: To get the same effect as Middleware (which can inject system prompts) when using MCP, add a `.cursor/rules/python/skills_prompt.mdc` file to your project root. This helps guide Cursor to use skills effectively. See [MCP Integration](docs/mcp-integration.md) for details.

> 💡 On Linux, change `/Users:/Users` to `/home:/home`

**Option B: LangChain Application (Middleware)**

```python
from agent_skills.core.middleware import SkillsMiddleware
from deepagents import create_deep_agent

# Configure skills_dir and host directory mount
middleware = SkillsMiddleware(
    skills_dir="/path/to/skills",
    host_mount="/Users:/Users",  # Optional, for scripts to access external files
)

agent = create_deep_agent(
    tools=[],
    system_prompt="You are a helpful assistant.",
    middleware=middleware.get_middlewares(),
)
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Tools Reference](docs/tools.md) | Detailed explanation of 6 `skills_*` tools |
| [MCP Integration](docs/mcp-integration.md) | Claude Desktop / Cursor configuration |
| [Middleware Integration](docs/middleware-integration.md) | LangChain native integration |
| [Examples](docs/examples.md) | 4 example programs |
| [Docker Environment](docs/docker-environment.md) | Pre-installed tools and environment variables |
| [Skill Format](docs/skill-format.md) | How to write and organize Skills |

---

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v

# Start MCP Server locally
uv run agent-skills-server
```

---

## License

Apache 2.0

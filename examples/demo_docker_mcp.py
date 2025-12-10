"""Docker Skills Demo (Interactive)

这是一个交互式 Agent Demo，展示了 Agent Skills 的完整能力。

## 特点
1. **Docker 运行**: 自动启动 Docker 容器运行 MCP Server
2. **宿主机目录挂载**: 挂载 /Users (macOS) 或 /home (Linux)，脚本可访问任意文件

## 使用方式

    python examples/demo_docker_mcp.py
    
    Agent 可以：
    - 使用 skills_ls(path="skills") 列出技能
    - 使用 skills_run 处理任意文件（通过绝对路径）

## 示例对话
- "查看 skills 目录下有哪些技能"
- "帮我创建一个新技能叫 hello-world"
- "用 pdf 技能将 /Users/xxx/doc.pdf 转换为 markdown"

Usage:
    python examples/demo_docker_mcp.py
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StdioConnection
from langchain_openai import ChatOpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# Import local modules if available (for skill discovery in client)
# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from agent_skills.core.skill_manager import SkillManager
    from agent_skills.mcp.prompts import SKILL_GUIDE_PROMPT
except ImportError:
    SKILL_GUIDE_PROMPT = ""
    SkillManager = None

# Configure logging
logging.getLogger("mcp").setLevel(logging.WARNING)

load_dotenv()

# Custom theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "tool_name": "bold magenta",
    "tool_args": "dim cyan",
    "user": "bold green",
    "agent": "bold blue",
})
console = Console(theme=custom_theme)

# User Home Directory for mounting
USER_HOME = Path.home()

# Base System Prompt
BASE_SYSTEM_PROMPT = """
You are a generic AI assistant powered by Dockerized Agent Skills.

# 工具权限

管理工具（skills_ls, skills_read, skills_write, skills_bash, skills_create）只能操作 /skills 目录。
如需访问外部文件，使用 skills_run 并在命令参数中传递绝对路径。

## 路径使用方式

1. **技能目录**：使用 `skills/` 前缀
   - `skills_ls(path="skills")` - 列出技能
   - `skills_read(path="skills/my-skill/SKILL.md")` - 读取技能

2. **外部文件**：通过 skills_run 使用绝对路径
   - `skills_run(name="pdf", command="python scripts/convert.py /Users/xxx/doc.pdf -o /Users/xxx/doc.md")`

# Available Tools
- `skills_ls`: List files in /skills directory
- `skills_read`: Read files from /skills directory
- `skills_write`: Write files to /skills directory
- `skills_bash`: Execute shell commands in /skills directory
- `skills_create`: Create new skills
- `skills_run`: Run skill scripts (can access external files via command args)

# Guidelines
1. Use `skills_ls()` to see workspace contents (user's project).
2. Use `skills_ls(path="skills")` to see available skills.
3. Use relative paths for workspace files, `skills/` prefix for skills.
"""

def print_tool_call(tool_name: str, tool_args: dict[str, Any]) -> None:
    """Pretty print tool call"""
    args_json = json.dumps(tool_args, indent=2, ensure_ascii=False)
    panel = Panel(
        Syntax(args_json, "json", theme="monokai", line_numbers=False),
        title=f"🔧 Tool Call: [tool_name]{tool_name}[/tool_name]",
        border_style="magenta",
        padding=(0, 1),
    )
    console.print(panel)

def print_tool_output(tool_name: str, output: str) -> None:
    """Pretty print tool output"""
    max_lines = 40
    lines = output.split("\n")
    display_output = "\n".join(lines[:max_lines])
    if len(lines) > max_lines:
        display_output += f"\n... (truncated, {len(output)} chars total)"
    
    panel = Panel(
        display_output,
        title=f"📤 Output from [tool_name]{tool_name}[/tool_name]",
        border_style="cyan",
        padding=(0, 1),
    )
    console.print(panel)

def print_streaming_text(text: str) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()

async def main():
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[error]Error: OPENAI_API_KEY not set![/error]")
        return

    # Docker arguments
    docker_cmd = "docker"
    docker_args = [
        "run", "-i", "--rm",
        # Force uv to use the container's venv, not the mounted host venv
        "-e", "UV_PROJECT_ENVIRONMENT=/app/.venv",
        # Mount Skills directory
        "-v", f"{PROJECT_ROOT}/agent_skills/skills:/skills",
        # Mount host directory for external file access
        "-v", f"{USER_HOME}:{USER_HOME}",
        # Image
        "agent-skills:latest"
    ]
    
    mount_info = f"📂 Skills: {PROJECT_ROOT}/agent_skills/skills → /skills"
    access_tip = f"💡 Host mount: {USER_HOME} → {USER_HOME} (for external file access)"

    console.print(Panel.fit(
        "[bold]🚀 Agent Skills Docker Interactive Demo[/bold]\n\n"
        f"🐳 Docker: {docker_cmd} run ...\n"
        f"{mount_info}\n"
        f"{access_tip}",
        border_style="green"
    ))

    # MCP Connection
    mcp_connections: dict[str, Any] = {
        "agent-skills": StdioConnection(
            transport="stdio",
            command=docker_cmd,
            args=docker_args,
        )
    }

    try:
        console.print("🔄 Connecting to Docker MCP Server...", style="dim")
        mcp_client = MultiServerMCPClient(mcp_connections)
        tools = await mcp_client.get_tools()

        # Display Tools
        table = Table(title="Available Tools", border_style="blue")
        table.add_column("Tool", style="tool_name")
        table.add_column("Description", style="dim")
        for t in tools:
            table.add_row(t.name, t.description[:60] + "...")
        console.print(table)

        # Build System Prompt
        skills_text = ""
        if SkillManager:
            # Discover local skills for context
            builtin_skills = PROJECT_ROOT / "agent_skills" / "skills"
            mgr = SkillManager(builtin_skills_dir=builtin_skills)
            skills = mgr.discover_skills()
            skills_text = "\n".join([f"- {s.name}: {s.description}" for s in skills])

        final_system_prompt = f"""{BASE_SYSTEM_PROMPT}

# Skill System Guide
{SKILL_GUIDE_PROMPT}

# Available Skills
{skills_text}
"""
        
        # Initialize Agent
        llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
        agent = create_agent(
            model=llm, 
            tools=tools, 
            system_prompt=final_system_prompt
        )

        # Interactive Loop
        message_history = []
        
        while True:
            try:
                console.print()
                user_input = console.input("[user]You → [/user]").strip()
                if not user_input: continue
                if user_input.lower() in ["exit", "quit"]: break
                
                message_history.append({"role": "user", "content": user_input})
                
                console.print()
                console.rule("[agent]🤖 Agent Response[/agent]", style="blue")
                
                accumulated_content = ""
                is_streaming = False

                async for event in agent.astream({"messages": message_history}, stream_mode="updates"):
                    chunk = event if not isinstance(event, tuple) else event[0]
                    
                    # Handle Agent Message / Thoughts
                    if "agent" in chunk or "model" in chunk:
                        node = chunk.get("agent") or chunk.get("model")
                        if node is None:
                            continue
                        messages = node.get("messages", [])
                        
                        for msg in messages:
                            # Stream text content
                            if hasattr(msg, "content") and msg.content:
                                text = ""
                                if isinstance(msg.content, str):
                                    text = msg.content
                                elif isinstance(msg.content, list):
                                    for item in msg.content:
                                        if isinstance(item, dict) and item.get("type") == "text":
                                            text += item.get("text", "")
                                
                                if text:
                                    if not is_streaming and not accumulated_content:
                                        console.print()
                                        is_streaming = True
                                    print_streaming_text(text)
                                    accumulated_content += text
                            
                            # Print Tool Calls
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                if is_streaming:
                                    console.print()
                                    is_streaming = False
                                for tc in msg.tool_calls:
                                    print_tool_call(tc["name"], tc["args"])

                    # Handle Tool Output
                    elif "tools" in chunk:
                        if is_streaming:
                            console.print()
                            is_streaming = False
                        
                        for msg in chunk["tools"]["messages"]:
                            print_tool_output(msg.name, str(msg.content))

                if is_streaming:
                    console.print()
                
                if accumulated_content:
                    message_history.append({"role": "assistant", "content": accumulated_content})

                console.print()
                console.rule(style="dim blue")

            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"\n[error]Error: {e}[/error]")

    except Exception as e:
        console.print(f"[error]Connection Failed: {e}[/error]")
        if "docker" in str(e).lower():
            console.print("[warning]Make sure Docker is running and the image 'agent-skills:latest' is built.[/warning]")

if __name__ == "__main__":
    asyncio.run(main())

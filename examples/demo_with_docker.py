"""终极版 Docker Skills Demo (Interactive)

这是一个通用的交互式 Agent Demo，展示了 Agent Skills 的完整能力。
它与 demo_skills.py 的主要区别在于：
1. **Docker 运行**: 自动启动 Docker 容器运行 MCP Server
2. **路径镜像**: 挂载宿主机根目录，让 Agent 可以直接通过绝对路径操作文件

你可以像这样与它对话：
- "查看 skills 目录下有哪些技能"
- "帮我创建一个新技能叫 hello-world"
- "读取 /Users/nanjiayan/Desktop/test.txt 的内容" (直接使用绝对路径!)

Usage:
    python examples/demo_with_docker.py
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
BASE_SYSTEM_PROMPT = f"""
You are a generic AI assistant powered by Dockerized Agent Skills.

# KEY CAPABILITY: Direct File Access
You are running in a Docker container that has **mirrored access** to the host filesystem.
This means you can access files on the user's computer using their **absolute paths**.

- ❌ DO NOT ask the user to upload files.
- ✅ DO use absolute paths directly (e.g., `/Users/username/Desktop/file.txt`).

# Available Tools
- `skills_bash`: Execute shell commands
- `skills_ls`: List files
- `skills_read`: Read files
- `skills_write`: Write files
- `skills_create`: Create new skills
- `skills_run`: Run skill scripts

# Guidelines
1. Always check `skills_ls` before assuming file existence.
2. Use `skills_ls(path="skills")` to see available skills.
3. If the user mentions a file, assume you can access it via its absolute path.
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

    # Docker arguments for Path Mirroring
    docker_cmd = "docker"
    docker_args = [
        "run", "-i", "--rm",
        # Force uv to use the container's venv, not the mounted host venv
        "-e", "UV_PROJECT_ENVIRONMENT=/app/.venv",
        # 1. Mount User Home -> User Home (The Magic)
        "-v", f"{USER_HOME}:{USER_HOME}",
        # 2. Mount Skills
        "-v", f"{PROJECT_ROOT}/agent_skills/skills:/skills:ro",
        # 3. Set Working Directory to current dir
        "-w", str(os.getcwd()),
        # 4. Image
        "agent-skills:latest"
    ]

    console.print(Panel.fit(
        "[bold]🚀 Agent Skills Docker Interactive Demo[/bold]\n\n"
        f"🐳 Docker Command: {docker_cmd} {' '.join(docker_args)}\n"
        f"📂 Host Access: Enabled ({USER_HOME})\n"
        "💡 Tip: You can ask me to read/write any file on your computer!",
        border_style="green"
    ))

    # MCP Connection
    mcp_connections = {
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
                        node = chunk.get("agent", chunk.get("model"))
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

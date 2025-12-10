"""终极版 Docker Skills Demo (Interactive)

这是一个通用的交互式 Agent Demo，展示了 Agent Skills 的完整能力。
它与 demo_skills.py 的主要区别在于：
1. **Docker 运行**: 自动启动 Docker 容器运行 MCP Server
2. **工作空间挂载**: 用户项目目录挂载到 /workspace

## 使用方式

### 挂载项目目录（推荐）
    python examples/demo_with_docker.py --workspace /path/to/your/project
    python examples/demo_with_docker.py -w ~/my-project
    
    Agent 可以直接访问：
    - "列出工作空间的文件"
    - "读取 src/main.py"
    - "运行 python main.py"

### 挂载整个用户目录（完全访问，向后兼容）
    python examples/demo_with_docker.py
    
    可以使用绝对路径：
    - "读取 /Users/me/Desktop/test.txt"

## 示例对话
- "查看 skills 目录下有哪些技能"
- "列出工作空间的文件"
- "帮我创建一个新技能叫 hello-world"

Usage:
    python examples/demo_with_docker.py
    python examples/demo_with_docker.py --workspace /path/to/project
"""

import argparse
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

# 文件访问方式

你运行在 Docker 容器中，有两个主要目录：
- `/skills` - 技能目录（可读写，用于创建和修改技能）
- `/workspace` - 工作空间（用户挂载的项目目录）

## 路径使用方式

1. **工作空间文件**（用户项目）：直接使用相对路径
   - `skills_ls()` - 列出工作空间
   - `skills_read(path="src/main.py")` - 读取文件
   - `skills_bash(command="python main.py")` - 执行命令

2. **技能目录**：使用 `skills/` 前缀
   - `skills_ls(path="skills")` - 列出技能
   - `skills_read(path="skills/my-skill/SKILL.md")` - 读取技能

3. **绝对路径**（如果用户挂载了完整文件系统）：直接使用

# Available Tools
- `skills_bash`: Execute shell commands
- `skills_ls`: List files
- `skills_read`: Read files
- `skills_write`: Write files
- `skills_create`: Create new skills
- `skills_run`: Run skill scripts

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

async def main(workspace_dir: str | None = None):
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[error]Error: OPENAI_API_KEY not set![/error]")
        return

    # Docker arguments
    docker_cmd = "docker"
    docker_args = [
        "run", "-i", "--rm",
        # Force uv to use the container's venv, not the mounted host venv
        "-e", "UV_PROJECT_ENVIRONMENT=/app/.venv",
    ]
    
    # Determine mount strategy
    if workspace_dir:
        # Mode: Mount specific directory to /workspace (recommended)
        workspace_path = Path(workspace_dir).resolve()
        if not workspace_path.exists():
            console.print(f"[error]Error: Directory '{workspace_dir}' does not exist![/error]")
            return
        
        docker_args.extend([
            # Mount user's project to /workspace
            "-v", f"{workspace_path}:/workspace",
        ])
        mount_info = f"📂 Workspace: {workspace_path} → /workspace"
        access_tip = "💡 Access files directly: skills_ls(), skills_read('src/main.py')"
    else:
        # Mode: Mount entire home directory (full access, backwards compatible)
        docker_args.extend([
            # Mount User Home -> User Home (The Magic)
            "-v", f"{USER_HOME}:{USER_HOME}",
            # Also set workspace to home for convenience
            "-e", f"SKILLS_WORKSPACE={USER_HOME}",
        ])
        mount_info = f"📂 Full Access: {USER_HOME}"
        access_tip = "💡 Use absolute paths or relative to home"
    
    # Common mounts
    docker_args.extend([
        # Mount Skills (read-write to allow creating/modifying skills)
        "-v", f"{PROJECT_ROOT}/agent_skills/skills:/skills",
        # Image
        "agent-skills:latest"
    ])

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

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Agent Skills Docker Interactive Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mount specific project directory to /workspace (recommended)
  python examples/demo_with_docker.py --workspace /path/to/your/project
  python examples/demo_with_docker.py -w ~/my-project
  
  # Full host access (mount entire home directory)
  python examples/demo_with_docker.py
"""
    )
    parser.add_argument(
        "-w", "--workspace",
        type=str,
        default=None,
        help="Path to mount as /workspace (your project directory). "
             "If not specified, mounts entire home directory for full access."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(workspace_dir=args.workspace))

"""Demo script for Agent Skills MCP integration with LangChain.

This script demonstrates how to use the agent-skills MCP server
with LangChain to create an interactive AI agent that can:
- Execute shell commands (bash)
- Manage background tasks (bg, jobs, kill)
- Discover and use skills via MCP Resources

Usage:
    python examples/demo_skills.py

Environment:
    OPENAI_API_KEY: Your OpenAI API key
"""

# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
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

# Import local modules for system prompt construction
# Add the directory containing agent_skills package to sys.path
agent_skills_pkg_path = os.path.join(os.path.dirname(__file__), "..", "agent_skills")
sys.path.append(agent_skills_pkg_path)

try:
    from agent_skills.core.skill_manager import SkillManager
    from agent_skills.mcp.prompts import SKILL_GUIDE_PROMPT
    from agent_skills.sandbox.sandbox import Sandbox, SandboxConfig
except ImportError:
    # Fallback if import fails (e.g. structure differences)
    print("Warning: Could not import local agent_skills modules. System prompt will be limited.")
    # Use dummy values
    skill_guide_prompt_content = ""
    SkillManager = None
    Sandbox = None
    SandboxConfig = None
else:
    skill_guide_prompt_content = SKILL_GUIDE_PROMPT

# Suppress internal logging
logging.getLogger("mcp").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("mcp.server.fastmcp").setLevel(logging.WARNING)

load_dotenv()

# Create a custom theme for beautiful output
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

# Base System prompt for the agent
BASE_SYSTEM_PROMPT = """\
You are a helpful AI assistant with access to a set of tools for file operations, 
command execution, and skill management.

## Available Tools

You have access to the following tools via MCP:
- `bash`: Execute shell commands (ls, cat, grep, python, etc.)
- `bg`: Run commands in background
- `jobs`: List background tasks
- `kill`: Terminate processes
- `skill`: Manage skills (list, read, create, validate)

## Guidelines

1. Use `bash` as your primary tool for file operations
2. When you need to learn how to do something, check if there's a relevant skill
3. Be concise and helpful in your responses
4. Always explain what you're doing before executing commands
5. When exploring a directory, start with `bash("ls -la")` to see what files exist
"""


def print_tool_call(tool_name: str, tool_args: dict[str, Any]) -> None:
    """Pretty print a tool call with Rich formatting."""
    # Format arguments as JSON with syntax highlighting
    args_json = json.dumps(tool_args, indent=2, ensure_ascii=False)
    
    # Create a panel for the tool call
    content = Text()
    content.append("📍 ", style="bold")
    content.append(tool_name, style="tool_name")
    
    # Create syntax highlighted args
    args_syntax = Syntax(args_json, "json", theme="monokai", line_numbers=False)
    
    panel = Panel(
        args_syntax,
        title=f"🔧 Tool Call: [tool_name]{tool_name}[/tool_name]",
        title_align="left",
        border_style="magenta",
        padding=(0, 1),
    )
    console.print(panel)


def print_tool_output(tool_name: str, output: str) -> None:
    """Pretty print tool output with Rich formatting."""
    # Truncate very long output (increased for skill content)
    max_lines = 80
    lines = output.split("\n")
    truncated = False
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True
        
    display_output = "\n".join(lines)
    if truncated:
        display_output += f"\n... (truncated, {len(output)} chars total)"
    
    # Try to detect output type for syntax highlighting
    lang = "text"
    if output.strip().startswith("{") or output.strip().startswith("["):
        try:
            json.loads(output)
            lang = "json"
        except json.JSONDecodeError:
            pass
    elif output.strip().startswith("```"):
        lang = "markdown"
    
    if lang != "text":
        content = Syntax(display_output, lang, theme="monokai", line_numbers=False, word_wrap=True)
    else:
        content = Text(display_output, style="dim")
    
    panel = Panel(
        content,
        title=f"📤 Output from [tool_name]{tool_name}[/tool_name]",
        title_align="left",
        border_style="cyan",
        padding=(0, 1),
    )
    console.print(panel)


def print_agent_message(content: str) -> None:
    """Pretty print agent's text message (non-streaming)."""
    if content.strip():
        console.print()
        console.print(Markdown(content))


def print_streaming_text(text: str) -> None:
    """Print streaming text immediately without newline."""
    # Use sys.stdout for true streaming output, avoiding Rich's buffering
    sys.stdout.write(text)
    sys.stdout.flush()


def print_welcome() -> None:
    """Print welcome banner."""
    welcome_text = """
╔══════════════════════════════════════════════════════════════╗
║          🤖 Agent Skills Interactive Demo                    ║
║                                                              ║
║  This agent can execute shell commands, manage background    ║
║  tasks, and use skills from the MCP server.                  ║
║                                                              ║
║  Commands: 'exit' or 'quit' to stop                          ║
╚══════════════════════════════════════════════════════════════╝
"""
    console.print(welcome_text, style="bold cyan")


def print_tools_table(tools: list[Any]) -> None:
    """Print available tools in a nice table."""
    table = Table(title="🛠️  Available Tools", border_style="blue")
    table.add_column("Tool", style="tool_name", no_wrap=True)
    table.add_column("Description", style="dim")
    
    for tool in tools:
        desc = getattr(tool, "description", "No description")
        # Truncate long descriptions
        if len(desc) > 80:
            desc = desc[:77] + "..."
        table.add_row(tool.name, desc)
    
    console.print(table)
    console.print()


async def main() -> None:
    """Run the interactive agent."""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[error]Error: OPENAI_API_KEY environment variable is not set.[/error]")
        console.print("Please set it in your .env file or environment.")
        sys.exit(1)

    # Get workspace path (default to current directory)
    workspace = os.getcwd()
    console.print(f"📁 Workspace: [info]{workspace}[/info]")
    console.print()

    # Get project root directory (contains pyproject.toml)
    project_root = os.path.join(os.path.dirname(__file__), "..")

    # Create MCP client configuration using StdioConnection TypedDict
    mcp_connections: dict[str, StdioConnection] = {
        "agent-skills": StdioConnection(
            transport="stdio",
            command="uv",
            args=[
                "run",
                "--directory",
                project_root,
                "agent-skills-server",
                "--workspace",
                workspace,
                "--quiet",  # Suppress MCP server logs
            ],
            env={
                **os.environ,
                "MCP_LOG_LEVEL": "ERROR",
                "LOGURU_LEVEL": "ERROR",
            },
        )
    }

    console.print("🚀 Starting MCP server...", style="info")
    console.print()

    # Use MultiServerMCPClient without context manager
    mcp_client = MultiServerMCPClient(mcp_connections)  # type: ignore[arg-type]
    
    # Get tools from MCP server
    try:
        tools = await mcp_client.get_tools()
        print_tools_table(tools)
        
        # Build enhanced system prompt with Skill Guide and Skill List
        skills_text = ""
        if SkillManager and Sandbox and SandboxConfig:
            # 1. Initialize local SkillManager to get skills list
            # Note: We use the same logic as the server to discover skills
            sandbox_config = SandboxConfig(workspace_root=workspace)
            sandbox = Sandbox(config=sandbox_config)
            skill_manager = SkillManager(sandbox)
            skills = skill_manager.discover_skills()
            
            # 2. Format skills list
            skills_text = "\n".join([f"- {skill.name}: {skill.description}" for skill in skills])
            
            num_skills = len(skills)
        else:
            skills_text = "(Skill discovery unavailable in client)"
            num_skills = 0
        
        # 3. Construct final system prompt
        system_prompt = f"""{BASE_SYSTEM_PROMPT}

# Skill System Guide

{skill_guide_prompt_content}

# Available Skills (Preloaded)

The following skills are currently available in your environment:

{skills_text}

You can read the full content of any skill using `skill("read", name="skill-name")`.
"""
        
        console.print(Panel(
            Markdown(f"**System Prompt Enhanced with:**\n- Skill Guide\n- {num_skills} Available Skills"),
            title="🧠 Context Loaded",
            border_style="green"
        ))

        # Create the LLM
        llm = ChatOpenAI(
            model="gpt-5.1",
            temperature=0.3,
            max_retries=3,       # 自动重试 3 次
            timeout=180,
            streaming=True,      # 强制开启流式输出
        )

        # Create agent using langchain 1.0+ API
        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
            name="skills-demo-agent",
        )

        # Print welcome banner
        print_welcome()

        # Track current tool call for matching with output
        current_tool_name = None
        accumulated_content = ""
        
        # Message history for multi-turn conversation
        message_history: list[dict[str, str]] = []

        while True:
            try:
                console.print()
                user_input = console.input("[user]You → [/user]").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n👋 Goodbye!", style="info")
                break

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit"]:
                console.print("👋 Goodbye!", style="info")
                break

            try:
                console.print()
                console.rule("[agent]🤖 Agent Response[/agent]", style="blue")
                accumulated_content = ""
                is_streaming_text = False  # Track if we're in text streaming mode
                
                # Add user message to history
                message_history.append({"role": "user", "content": user_input})

                async for event in agent.astream(
                    {"messages": message_history},  # type: ignore[arg-type]
                    stream_mode="updates",
                ):
                    # Handle different event types
                    chunk: dict[str, Any]
                    if isinstance(event, tuple):
                        chunk = event[0]
                    else:
                        chunk = event  
                    
                    # Handle model/agent updates (thoughts, tool calls, responses)
                    if "agent" in chunk or "model" in chunk:
                        node_key = "agent" if "agent" in chunk else "model"
                        messages: list[Any] = chunk[node_key].get("messages", [])
                        for message in messages:
                            # IMPORTANT: Process content BEFORE tool_calls
                            # This ensures the agent's explanation appears before the tool call panel
                            
                            # 1. Text content - stream in real-time (FIRST)
                            if hasattr(message, "content") and message.content:
                                text_chunk = ""
                                if isinstance(message.content, str):
                                    text_chunk = message.content
                                elif isinstance(message.content, list):
                                    for item in message.content:
                                        if isinstance(item, dict) and item.get("type") == "text":
                                            text_chunk += item.get("text", "")
                                
                                if text_chunk:
                                    # Start streaming indicator if first text
                                    if not is_streaming_text and not accumulated_content:
                                        console.print()  # New line before streaming
                                        is_streaming_text = True
                                    
                                    # Stream the text chunk immediately
                                    print_streaming_text(text_chunk)
                                    accumulated_content += text_chunk
                            
                            # 2. Tool calls - end text streaming, print tool call panel (AFTER content)
                            if hasattr(message, "tool_calls") and message.tool_calls:
                                if is_streaming_text:
                                    console.print()  # End the streaming line
                                    is_streaming_text = False
                                
                                for tool_call in message.tool_calls:
                                    current_tool_name = tool_call["name"]
                                    print_tool_call(tool_call["name"], tool_call["args"])

                    # Handle tool outputs - print panel, then resume streaming
                    elif "tools" in chunk:
                        if is_streaming_text:
                            console.print()  # End the streaming line
                            is_streaming_text = False
                        
                        tool_messages: list[Any] = chunk["tools"]["messages"]
                        for message in tool_messages:
                            tool_name = getattr(message, "name", current_tool_name) or "unknown"
                            print_tool_output(tool_name, str(message.content))

                # End streaming and save to history
                if is_streaming_text:
                    console.print()  # Final newline
                
                if accumulated_content.strip():
                    message_history.append({"role": "assistant", "content": accumulated_content})
                
                console.print()  # Extra spacing
                console.rule(style="dim blue")

            except Exception as e:
                console.print(f"\n[error]Error: {e}[/error]")
                import traceback
                console.print(traceback.format_exc(), style="dim red")
                
    finally:
        pass


if __name__ == "__main__":
    asyncio.run(main())

"""Deep Agent with Skills Middleware Integration.

This script demonstrates how to use Deep Agents with the Agent Skills Middleware,
combining the power of:
- 🔍 Internet Search (Tavily)
- 📁 Local File System (via FilesystemMiddleware with LocalFilesystemBackend)
- 🛠️ Skills System (via DockerSkillsMiddleware - NO MCP!)
- 📝 Task Planning (write_todos)
- 🤖 Subagents (spawn_subagent)

与 demo_deepagent.py 的区别：
- 使用 DockerSkillsMiddleware 替代 MCP Client
- 更简洁的集成方式，不需要 langchain-mcp-adapters
- Prompt 和 Tools 通过 Python 原生方式注入

工具分工：
- DeepAgent 内置文件工具 (ls, read_file, write_file, edit_file, glob, grep)
  → 操作本地 examples/workspace 目录
- Skills Middleware 工具 (skills_bash, skills_run, skills_create 等)
  → 通过 Docker 操作技能系统

Usage:
    # 安装依赖
    uv pip install -e ".[deepagent]"
    uv pip install docker  # Middleware 需要 docker 包
    
    # 构建 Docker 镜像
    docker build -t agent-skills:latest -f docker_config/Dockerfile .
    
    # 运行
    python examples/demo_middleware.py

Environment Variables:
    ANTHROPIC_API_KEY: Your Anthropic API key (默认后端)
    TAVILY_API_KEY: Your Tavily API key (用于网络搜索)
    OPENAI_API_KEY: Your OpenAI API key (可选后端)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# Load environment variables
load_dotenv()

# Project paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
WORKSPACE_DIR = SCRIPT_DIR / "workspace"
SKILLS_DIR = PROJECT_ROOT / "agent_skills" / "skills"

# Suppress noisy loggers
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("docker").setLevel(logging.WARNING)

# Import local modules
sys.path.insert(0, str(PROJECT_ROOT))
try:
    from agent_skills.core.middleware import DockerSkillsMiddleware
except ImportError as e:
    print(f"Error importing agent_skills: {e}")
    print("Make sure you're running from the project root.")
    sys.exit(1)

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
    "thinking": "dim cyan italic",
})

console = Console(theme=custom_theme)


# ============================================================================
# Local Filesystem Backend - 实现 FilesystemBackend 协议
# ============================================================================

class LocalFilesystemBackend:
    """本地文件系统后端，将 DeepAgent 的文件操作指向指定目录。
    
    实现了 FilesystemBackend 协议，使 DeepAgent 的内置文件工具
    (ls, read_file, write_file, edit_file, glob, grep) 可以操作真实的本地文件系统。
    """
    
    def __init__(self, root_dir: str | Path):
        """初始化本地文件系统后端。
        
        Args:
            root_dir: 根目录路径，所有文件操作都限制在此目录内
        """
        self.root = Path(root_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
    
    def _safe_path(self, path: str) -> Path:
        """确保路径在 root 目录内，防止路径穿越攻击。"""
        clean_path = path.lstrip("/")
        if not clean_path:
            return self.root
        
        full = (self.root / clean_path).resolve()
        
        if not str(full).startswith(str(self.root)):
            raise ValueError(f"Path '{path}' is outside workspace directory")
        
        return full
    
    def ls_info(self, path: str) -> list[dict[str, Any]]:
        """列出目录内容。"""
        try:
            safe = self._safe_path(path)
            if not safe.exists():
                return []
            if safe.is_file():
                stat = safe.stat()
                return [{
                    "name": safe.name,
                    "path": "/" + str(safe.relative_to(self.root)),
                    "is_dir": False,
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                }]
            
            items = []
            for item in sorted(safe.iterdir()):
                rel_path = "/" + str(item.relative_to(self.root))
                stat = item.stat()
                items.append({
                    "name": item.name,
                    "path": rel_path,
                    "is_dir": item.is_dir(),
                    "size": stat.st_size if item.is_file() else 0,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                })
            return items
        except Exception as e:
            return [{"error": str(e)}]
    
    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """读取文件内容。"""
        safe = self._safe_path(file_path)
        if not safe.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if safe.is_dir():
            raise IsADirectoryError(f"'{file_path}' is a directory")
        
        content = safe.read_text(encoding="utf-8")
        lines = content.split("\n")
        selected = lines[offset:offset + limit]
        
        numbered = []
        for i, line in enumerate(selected, start=offset + 1):
            numbered.append(f"{i:4d}|{line}")
        
        return "\n".join(numbered)
    
    def write(self, file_path: str, content: str) -> Any:
        """写入文件。"""
        from deepagents.backends.filesystem import WriteResult
        
        try:
            safe = self._safe_path(file_path)
            safe.parent.mkdir(parents=True, exist_ok=True)
            safe.write_text(content, encoding="utf-8")
            return WriteResult(error=None, path=file_path, files_update=None)
        except Exception as e:
            return WriteResult(error=str(e), path=file_path, files_update=None)
    
    def edit(
        self, file_path: str, old_string: str, new_string: str, replace_all: bool = False
    ) -> Any:
        """编辑文件，替换字符串。"""
        from deepagents.backends.filesystem import EditResult
        
        try:
            safe = self._safe_path(file_path)
            if not safe.exists():
                return EditResult(
                    error=f"File not found: {file_path}",
                    path=file_path,
                    files_update=None,
                    occurrences=0,
                )
            
            content = safe.read_text(encoding="utf-8")
            
            if old_string not in content:
                return EditResult(
                    error=f"String not found in file",
                    path=file_path,
                    files_update=None,
                    occurrences=0,
                )
            
            if replace_all:
                new_content = content.replace(old_string, new_string)
                count = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                count = 1
            
            safe.write_text(new_content, encoding="utf-8")
            return EditResult(
                error=None,
                path=file_path,
                files_update=None,
                occurrences=count,
            )
        except Exception as e:
            return EditResult(error=str(e), path=file_path, files_update=None, occurrences=0)
    
    def glob_info(self, pattern: str, path: str = "/") -> list[dict[str, Any]]:
        """使用 glob 模式搜索文件。"""
        safe = self._safe_path(path)
        if not safe.exists():
            return []
        
        results = []
        for item in safe.rglob(pattern):
            rel_path = "/" + str(item.relative_to(self.root))
            stat = item.stat()
            results.append({
                "name": item.name,
                "path": rel_path,
                "is_dir": item.is_dir(),
                "size": stat.st_size if item.is_file() else 0,
            })
        return results
    
    def grep_raw(
        self, pattern: str, path: str | None = None, glob: str | None = None
    ) -> list[dict[str, Any]] | str:
        """使用正则表达式搜索文件内容。"""
        search_path = self._safe_path(path or "/")
        
        if not search_path.exists():
            return f"Path not found: {path}"
        
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"Invalid regex pattern: {e}"
        
        results = []
        files_to_search = []
        
        if search_path.is_file():
            files_to_search = [search_path]
        else:
            glob_pattern = glob or "*"
            files_to_search = list(search_path.rglob(glob_pattern))
        
        for file_path in files_to_search:
            if file_path.is_dir():
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
                for i, line_text in enumerate(content.split("\n"), 1):
                    if regex.search(line_text):
                        rel_path = "/" + str(file_path.relative_to(self.root))
                        results.append({
                            "path": rel_path,
                            "line": i,
                            "text": line_text,
                        })
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return results
    
    def download_files(self, paths: list[str]) -> list[Any]:
        """下载文件（返回文件内容）。"""
        from deepagents.backends.protocol import FileDownloadResponse
        
        results = []
        for path in paths:
            try:
                safe = self._safe_path(path)
                if not safe.exists():
                    results.append(FileDownloadResponse(path=path, content=None, error="file_not_found"))
                elif safe.is_dir():
                    results.append(FileDownloadResponse(path=path, content=None, error="is_directory"))
                else:
                    content = safe.read_bytes()
                    results.append(FileDownloadResponse(path=path, content=content, error=None))
            except PermissionError:
                results.append(FileDownloadResponse(path=path, content=None, error="permission_denied"))
            except Exception:
                results.append(FileDownloadResponse(path=path, content=None, error="invalid_path"))
        return results
    
    def upload_files(self, files: list[tuple[str, bytes]]) -> list[Any]:
        """上传文件（写入二进制内容）。"""
        from deepagents.backends.protocol import FileUploadResponse
        
        results = []
        for path, content in files:
            try:
                safe = self._safe_path(path)
                if safe.is_dir():
                    results.append(FileUploadResponse(path=path, error="is_directory"))
                else:
                    safe.parent.mkdir(parents=True, exist_ok=True)
                    safe.write_bytes(content)
                    results.append(FileUploadResponse(path=path, error=None))
            except PermissionError:
                results.append(FileUploadResponse(path=path, error="permission_denied"))
            except Exception:
                results.append(FileUploadResponse(path=path, error="invalid_path"))
        return results


# ============================================================================
# Tool Creation Functions
# ============================================================================

def create_search_tool():
    """Create the Tavily internet search tool."""
    try:
        from tavily import TavilyClient
    except ImportError:
        console.print("[warning]Warning: tavily-python not installed. Search disabled.[/warning]")
        return None
    
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        console.print("[warning]Warning: TAVILY_API_KEY not set. Search functionality disabled.[/warning]")
        return None
    
    tavily_client = TavilyClient(api_key=api_key)
    
    def internet_search(
        query: str,
        max_results: int = 5,
        topic: Literal["general", "news", "finance"] = "general",
        include_raw_content: bool = False,
    ) -> dict:
        """Search the internet for information.
        
        Args:
            query: The search query string
            max_results: Maximum number of results to return (default: 5)
            topic: Search topic category - "general", "news", or "finance"
            include_raw_content: Whether to include raw page content
            
        Returns:
            Search results with titles, URLs, and snippets
        """
        return tavily_client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic=topic,
        )
    
    console.print("[success]✓ Internet search enabled (Tavily)[/success]")
    return internet_search


def create_skills_middleware():
    """Create the Docker Skills Middleware."""
    try:
        console.print("🐳 Initializing Docker Skills Middleware...", style="dim")
        
        # Ensure workspace exists
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create middleware
        middleware = DockerSkillsMiddleware(
            workspace_dir=str(WORKSPACE_DIR),
            skills_dir=str(SKILLS_DIR),
        )
        
        # Get tools from middleware
        tools = middleware.get_tools()
        
        console.print(f"[success]✓ Skills Middleware initialized ({len(tools)} tools available)[/success]")
        return middleware, tools
        
    except Exception as e:
        console.print(f"[error]Failed to initialize Skills Middleware: {e}[/error]")
        console.print("[warning]Make sure Docker is running and 'agent-skills:latest' image is built.[/warning]")
        console.print("[info]Build with: docker build -t agent-skills:latest -f docker_config/Dockerfile .[/info]")
        import traceback
        console.print(traceback.format_exc(), style="dim red")
        return None, []


# ============================================================================
# System Prompt and UI
# ============================================================================

def get_system_prompt(skills_prompt: str = "") -> str:
    """Generate the system prompt for the deep agent."""
    return f"""You are an expert AI assistant with powerful skills and tools. Your job is to help users with 
research, analysis, coding, and any tasks that require gathering and synthesizing information.

## Your Capabilities

### 1. Internet Search (`internet_search`)
Use this to search the web for current information:
- Search for general topics, news, or financial information
- Specify the number of results needed

### 2. Local File Operations (Built-in via FilesystemMiddleware)
You have direct access to the local workspace directory:
**Workspace**: `{WORKSPACE_DIR}`

**内置文件工具** (paths start with `/`):
- `ls(path="/")` - 列出文件和目录
- `read_file(file_path="/report.md")` - 读取文件内容
- `write_file(file_path="/output.txt", content="...")` - 写入文件
- `edit_file(file_path, old_string, new_string)` - 编辑文件
- `glob(pattern="*.md", path="/")` - 搜索文件
- `grep(pattern="TODO", path="/")` - 搜索文件内容

**注意**: 所有路径以 `/` 开头，代表 workspace 根目录。

### 3. Skills System (Docker Middleware - 原生集成)
For skill-related operations, use the `skills_*` tools:
- `skills_ls(path="skills")` - 列出可用技能
- `skills_read(path="skills/pdf/SKILL.md")` - 读取技能文档
- `skills_run(name="pdf", command="python scripts/convert_pdf_to_images.py input.pdf")` - 运行技能
- `skills_create(name="my-skill", description="...", instructions="...")` - 创建新技能
- `skills_bash(command="python script.py")` - 在 Docker 中执行命令

**Skills 目录映射**:
- 工作空间: `{WORKSPACE_DIR}` → Docker `/workspace`
- 技能目录: `{SKILLS_DIR}` → Docker `/skills`

### 4. Task Planning (Built-in `write_todos`)
For complex tasks, use the todo system to plan and track progress.

{skills_prompt}

## Tool Usage Guidelines

**常规文件操作** → 使用内置文件工具 (ls, read_file, write_file)
**技能系统操作** → 使用 skills_* 工具
**网络搜索** → 使用 internet_search
**任务规划** → 使用 write_todos

## Response Style
- Be concise but comprehensive
- Use markdown formatting for readability
- 默认使用中文回复用户
"""


def print_welcome() -> None:
    """Print welcome banner."""
    welcome_text = f"""
╔══════════════════════════════════════════════════════════════════╗
║     🧠 Deep Agent + Skills Middleware Demo                        ║
║                                                                   ║
║  This agent combines:                                             ║
║  • 🔍 Internet Search (Tavily)                                    ║
║  • 📁 Local File System (FilesystemMiddleware)                    ║
║  • 🐳 Skills System (DockerSkillsMiddleware)                      ║
║  • 📝 Task Planning (write_todos)                                 ║
║                                                                   ║
║  Workspace: {str(WORKSPACE_DIR):<43} ║
║                                                                   ║
║  💡 与 MCP 版本的区别:                                             ║
║     - 使用 Python 原生 Middleware，无需 MCP 协议                    ║
║     - 更低延迟，更简洁的集成                                        ║
║                                                                   ║
║  Commands:                                                        ║
║    'exit' or 'quit' - Stop the demo                               ║
║    'clear' - Clear conversation history                           ║
║                                                                   ║
╚══════════════════════════════════════════════════════════════════╝
"""
    console.print(welcome_text, style="bold cyan")


def print_tool_call(tool_name: str, tool_args: dict[str, Any]) -> None:
    """Pretty print a tool call with Rich formatting."""
    args_json = json.dumps(tool_args, indent=2, ensure_ascii=False)
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
    max_chars = 2000
    truncated = False
    if len(output) > max_chars:
        output = output[:max_chars]
        truncated = True
        
    display_output = output
    if truncated:
        display_output += "\n... (truncated)"
    
    lang = "text"
    if output.strip().startswith("{") or output.strip().startswith("["):
        try:
            json.loads(output)
            lang = "json"
        except json.JSONDecodeError:
            pass
    
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


def check_api_keys() -> str:
    """Check for available API keys and return the backend to use."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    if anthropic_key:
        console.print("[success]✓ Using Anthropic (Claude) as backend[/success]")
        return "anthropic"
    elif openai_key:
        console.print("[success]✓ Using OpenAI as backend[/success]")
        return "openai"
    else:
        console.print("[error]Error: No API key found.[/error]")
        console.print("Please set ANTHROPIC_API_KEY or OPENAI_API_KEY in your environment.")
        sys.exit(1)


async def run_agent_with_streaming(agent: Any, user_input: str) -> str:
    """Run agent with streaming events to show tool calls."""
    final_response = ""
    shown_tool_calls: set[str] = set()
    
    async for event in agent.astream_events(
        {"messages": [{"role": "user", "content": user_input}]},
        config={"recursion_limit": 50},
        version="v2",
    ):
        event_type = event.get("event", "")
        event_name = event.get("name", "")
        data = event.get("data", {})
        
        if event_type == "on_tool_start":
            tool_input = data.get("input", {})
            if isinstance(tool_input, dict):
                display_input = {}
                for k, v in tool_input.items():
                    try:
                        json.dumps(v)
                        display_input[k] = v
                    except (TypeError, ValueError):
                        display_input[k] = f"<{type(v).__name__}>"
                
                try:
                    call_key = f"{event_name}:{json.dumps(display_input, sort_keys=True)}"
                except (TypeError, ValueError):
                    call_key = f"{event_name}:{id(tool_input)}"
                
                if call_key not in shown_tool_calls:
                    shown_tool_calls.add(call_key)
                    print_tool_call(event_name, display_input)
        
        elif event_type == "on_tool_end":
            output = data.get("output", "")
            if hasattr(output, "content"):
                output = output.content
            if output:
                print_tool_output(event_name, str(output))
        
        elif event_type == "on_chain_end" and event_name == "LangGraph":
            output = data.get("output", {})
            if isinstance(output, dict) and "messages" in output:
                messages = output["messages"]
                if messages:
                    last_msg = messages[-1]
                    if hasattr(last_msg, "content"):
                        content = last_msg.content
                        if isinstance(content, list):
                            text_parts = []
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    text_parts.append(item.get("text", ""))
                            final_response = "\n".join(text_parts)
                        else:
                            final_response = str(content)
    
    return final_response


# ============================================================================
# Main Entry Point
# ============================================================================

async def main_async() -> None:
    """Run the interactive deep agent (async version)."""
    try:
        from deepagents import create_deep_agent
    except ImportError:
        console.print("[error]Error: deepagents not installed.[/error]")
        console.print("Run: uv pip install -e '.[deepagent]'")
        sys.exit(1)
    
    console.print("🚀 Initializing Deep Agent with Skills Middleware...\n", style="info")
    
    # Check API keys
    backend = check_api_keys()
    
    # Create local filesystem backend for DeepAgent's built-in file tools
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    fs_backend = LocalFilesystemBackend(WORKSPACE_DIR)
    console.print(f"[success]✓ Local filesystem enabled (workspace: {WORKSPACE_DIR})[/success]")
    
    # Collect custom tools
    custom_tools: list[Any] = []
    
    # Add search tool
    search_tool = create_search_tool()
    if search_tool:
        custom_tools.append(search_tool)
    
    # Initialize Skills Middleware (replaces MCP client)
    middleware, skills_tools = create_skills_middleware()
    if skills_tools:
        custom_tools.extend(skills_tools)
    
    # Get skills prompt from middleware (includes SKILL_GUIDE_PROMPT + available skills)
    skills_prompt = ""
    if middleware:
        try:
            skills_prompt = middleware.get_prompt()
            skills_count = len(middleware.skill_manager.discover_skills())
            console.print(f"[success]✓ Discovered {skills_count} skills[/success]")
        except Exception as e:
            console.print(f"[warning]Could not get skills prompt: {e}[/warning]")
    
    console.print()
    
    # Store llm reference for OpenAI backend
    llm = None
    
    # Create the deep agent with LocalFilesystemBackend
    try:
        if backend == "anthropic":
            agent = create_deep_agent(
                tools=custom_tools,
                backend=fs_backend,  # type: ignore[arg-type]
                system_prompt=get_system_prompt(skills_prompt),
            )
        else:
            from langchain_openai import ChatOpenAI
            
            llm = ChatOpenAI(
                model="gpt-4.1",
                temperature=0.3,
            )
            agent = create_deep_agent(
                tools=custom_tools,
                backend=fs_backend,  # type: ignore[arg-type]
                system_prompt=get_system_prompt(skills_prompt),
                model=llm,
            )
    except Exception as e:
        console.print(f"[error]Failed to create agent: {e}[/error]")
        import traceback
        console.print(traceback.format_exc(), style="dim red")
        sys.exit(1)
    
    # Print welcome and tools info
    print_welcome()
    
    # Display all available tools
    console.print(Panel(
        Markdown(f"""**🔍 搜索工具：**
- `internet_search` - 网络搜索 (Tavily)

**📁 本地文件工具（DeepAgent 内置，工作目录：`{WORKSPACE_DIR}`）：**
- `ls` - 列出文件和目录
- `read_file` - 读取文件内容  
- `write_file` - 写入文件
- `edit_file` - 编辑文件（替换字符串）
- `glob` - 搜索文件
- `grep` - 搜索文件内容

**🐳 Skills Middleware 工具（Docker 隔离执行）：**
- `skills_ls` - 列出技能/文件
- `skills_read` - 读取文件
- `skills_write` - 写入文件
- `skills_create` - 创建新技能
- `skills_run` - 运行技能脚本（支持 uv 依赖隔离）
- `skills_bash` - 在 Docker 中执行命令

**📂 目录映射：**
- 本地工作空间: `{WORKSPACE_DIR}`
- Docker 工作空间: `/workspace`
- Docker 技能目录: `/skills`

**🧠 Deep Agent 内置：**
- `write_todos` / `read_todos` - 任务规划
- `task` - 子智能体委托

**💡 Middleware vs MCP：**
- 本 Demo 使用 **DockerSkillsMiddleware**（Python 原生）
- 对比 demo_deepagent.py 使用 MCP Client（JSON-RPC 协议）
- Middleware 方式延迟更低，集成更简洁
"""),
        title="🛠️ Agent Capabilities",
        border_style="green"
    ))
    
    console.print()
    
    # Interactive loop
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
        
        if user_input.lower() == "clear":
            console.print("[info]Conversation cleared.[/info]")
            if backend == "anthropic":
                agent = create_deep_agent(
                    tools=custom_tools,
                    backend=fs_backend,  # type: ignore[arg-type]
                    system_prompt=get_system_prompt(skills_prompt),
                )
            else:
                agent = create_deep_agent(
                    tools=custom_tools,
                    backend=fs_backend,  # type: ignore[arg-type]
                    system_prompt=get_system_prompt(skills_prompt),
                    model=llm,
                )
            continue
        
        try:
            console.print()
            console.rule("[agent]🤖 Deep Agent Response[/agent]", style="blue")
            console.print()
            
            final_response = await run_agent_with_streaming(agent, user_input)
            
            if final_response:
                console.print()
                console.print(Markdown(final_response))
            
            console.print()
            console.rule(style="dim blue")
            
        except Exception as e:
            console.print(f"\n[error]Error: {e}[/error]")
            import traceback
            console.print(traceback.format_exc(), style="dim red")


def main() -> None:
    """Entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()


"""LangChain-native Skills Middleware using official decorators.

This module provides middleware for injecting skills capabilities into LangChain agents
using the official AgentMiddleware protocol:
- @dynamic_prompt for system prompt injection
- @before_model(tools=[...]) for tools injection  
- @before_agent / @after_agent for lifecycle management

Reference: https://reference.langchain.com/python/langchain/middleware/
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool

from agent_skills.core.skill_manager import SkillManager
from agent_skills.core.docker_runner import DockerRunner
from agent_skills.core.tools_factory import DockerToolFactory
from agent_skills.mcp.prompts import SKILL_GUIDE_PROMPT

if TYPE_CHECKING:
    from langchain.agents.middleware import AgentMiddleware, ModelRequest

# Lazy import LangChain middleware components
_lc_middleware_loaded = False
_dynamic_prompt: Any = None
_before_model: Any = None
_before_agent: Any = None
_after_agent: Any = None
_AgentMiddleware: Any = None
_ModelRequest: Any = None


def _ensure_lc_middleware() -> bool:
    """Lazily import LangChain middleware components."""
    global _lc_middleware_loaded, _dynamic_prompt, _before_model, _before_agent, _after_agent
    global _AgentMiddleware, _ModelRequest
    
    if _lc_middleware_loaded:
        return True
    
    try:
        from langchain.agents.middleware import (
            dynamic_prompt,
            before_model,
            before_agent,
            after_agent,
            AgentMiddleware,
            ModelRequest,
        )
        _dynamic_prompt = dynamic_prompt
        _before_model = before_model
        _before_agent = before_agent
        _after_agent = after_agent
        _AgentMiddleware = AgentMiddleware
        _ModelRequest = ModelRequest
        _lc_middleware_loaded = True
        return True
    except ImportError as e:
        raise ImportError(
            f"LangChain AgentMiddleware is required. Please install/update langchain>=0.3. Error: {e}"
        )


class SkillsMiddleware:
    """
    Factory class that creates LangChain-native middleware for Agent Skills.
    
    This class manages:
    - DockerRunner: Container lifecycle for skill execution
    - SkillManager: Skill discovery and management
    - DockerToolFactory: Creation of skills_* tools
    
    Use get_middlewares() to get all middleware instances for create_deep_agent().
    
    Example:
        # Minimal: only skills directory (recommended when Agent has its own filesystem)
        middleware_factory = SkillsMiddleware(
            skills_dir="/path/to/skills",
        )
        
        # With host mount: for scripts that need to access external files
        middleware_factory = SkillsMiddleware(
            skills_dir="/path/to/skills",
            host_mount="/Users:/Users",  # macOS, or "/home:/home" for Linux
        )
        
        # Legacy: workspace_dir (deprecated, use host_mount instead)
        middleware_factory = SkillsMiddleware(
            skills_dir="/path/to/skills",
            workspace_dir="/path/to/workspace",  # deprecated
        )
        
        agent = create_deep_agent(
            model="claude-sonnet-4-20250514",
            tools=custom_tools,
            middleware=middleware_factory.get_middlewares(),
        )
    """

    def __init__(
        self, 
        skills_dir: Optional[str] = None,
        workspace_dir: Optional[str] = None,
        host_mount: Optional[str] = None,
    ):
        """
        Initialize the middleware factory.
        
        Args:
            skills_dir: Local path to custom skills (mounted to /skills in Docker).
                        If None, uses built-in skills directory.
            workspace_dir: (Deprecated) Optional local path to workspace (mounted to /workspace).
                          Use host_mount instead for more flexibility.
            host_mount: Optional mount specification in "host_path:container_path" format.
                       Example: "/Users:/Users" (macOS) or "/home:/home" (Linux).
                       This allows scripts to access external files via absolute paths.
        """
        _ensure_lc_middleware()
        
        # Default skills directory
        default_skills = Path(__file__).parent.parent / "skills"
        self.skills_dir = Path(skills_dir).resolve() if skills_dir else default_skills
        self._default_skills_dir = default_skills
        
        # Workspace is optional (deprecated)
        self.workspace_dir: Optional[Path] = Path(workspace_dir).resolve() if workspace_dir else None
        
        # Parse host_mount into extra_mounts dict
        self.extra_mounts: Optional[Dict[str, str]] = None
        if host_mount:
            parts = host_mount.split(":")
            if len(parts) == 2:
                self.extra_mounts = {parts[0]: parts[1]}
            else:
                raise ValueError(f"Invalid host_mount format: '{host_mount}'. Expected 'host_path:container_path'")
        
        # Initialize components (lazy start for runner)
        self.runner = DockerRunner()
        
        self.skill_manager = SkillManager(
            skills_dirs=[self.skills_dir] if skills_dir else None,
            builtin_skills_dir=default_skills
        )

        self.tool_factory = DockerToolFactory(
            runner=self.runner,
            skill_manager=self.skill_manager,
            host_workspace=self.workspace_dir,
            host_skills=self.skills_dir
        )
        
        # Cache for middleware instances
        self._middlewares: Optional[List[Any]] = None

    def get_tools(self) -> List[BaseTool]:
        """Return the list of Docker-backed skills tools."""
        return self.tool_factory.get_tools()

    def get_prompt(self) -> str:
        """
        Get the complete skill system prompt (SKILL_GUIDE_PROMPT + Available Skills).
        """
        skills = self.skill_manager.discover_skills()
        skills_text = "\n".join([f"- {s.name}: {s.description}" for s in skills])
        if not skills_text:
            skills_text = "(No skills currently available)"

        return f"""
{SKILL_GUIDE_PROMPT}

## Currently Available Skills
{skills_text}
""".strip()

    def get_middlewares(self, stop_on_exit: bool = False) -> List[Any]:
        """
        Get all LangChain-native middleware instances.
        
        Returns a list of middleware that can be passed directly to create_deep_agent():
        1. Lifecycle middleware (before_agent/after_agent): Manages Docker container
        2. Prompt middleware (dynamic_prompt): Injects skill guide into system prompt
        3. Tools middleware (before_model with tools): Injects skills_* tools
        
        Args:
            stop_on_exit: Whether to stop the Docker container after agent completes
            
        Returns:
            List of AgentMiddleware instances
        """
        if self._middlewares is not None:
            return self._middlewares
        
        middlewares: List[Any] = []
        
        # 1. Lifecycle middleware - manages Docker container
        lifecycle_mw = self._create_lifecycle_middleware(stop_on_exit)
        middlewares.append(lifecycle_mw)
        
        # 2. Prompt middleware - injects skill guide using @dynamic_prompt
        prompt_mw = self._create_prompt_middleware()
        middlewares.append(prompt_mw)
        
        # 3. Tools middleware - injects skills_* tools using @before_model(tools=[...])
        tools_mw = self._create_tools_middleware()
        middlewares.append(tools_mw)
        
        self._middlewares = middlewares
        return middlewares

    def _create_lifecycle_middleware(self, stop_on_exit: bool) -> Any:
        """Create middleware for Docker container lifecycle management."""
        runner = self.runner
        host_workspace = str(self.workspace_dir) if self.workspace_dir else None
        host_skills = str(self.skills_dir)
        extra_mounts = self.extra_mounts
        
        if stop_on_exit:
            # Need both before_agent and after_agent - create a class-based middleware
            class SkillsLifecycleMiddleware(_AgentMiddleware):  # type: ignore[misc]
                name = "skills_lifecycle"
                
                def before_agent(self, state: Any, *, runtime: Any, config: Any) -> Any:
                    runner.start(host_skills, host_workspace, extra_mounts)
                    return state
                
                def after_agent(self, state: Any, *, runtime: Any, config: Any) -> Any:
                    try:
                        runner.stop(remove=False)
                    except Exception:
                        pass
                    return state
            
            return SkillsLifecycleMiddleware()
        else:
            # Only need before_agent - use decorator
            @_before_agent  # type: ignore[misc]
            def skills_lifecycle_start(state: Any, runtime: Any) -> None:
                """Start Docker container before agent execution (idempotent)."""
                runner.start(host_skills, host_workspace, extra_mounts)
                return None
            
            return skills_lifecycle_start

    def _create_prompt_middleware(self) -> Any:
        """Create middleware for dynamic system prompt injection using @dynamic_prompt."""
        skill_manager = self.skill_manager
        
        @_dynamic_prompt  # type: ignore[misc]
        def skills_prompt(request: Any) -> str | SystemMessage:
            """Dynamically inject skill guide and available skills into system prompt."""
            # Build skills list
            skills = skill_manager.discover_skills()
            skills_text = "\n".join([f"- {s.name}: {s.description}" for s in skills])
            if not skills_text:
                skills_text = "(No skills currently available)"
            
            injection = f"""
{SKILL_GUIDE_PROMPT}

## Currently Available Skills
{skills_text}
""".strip()
            
            # Get existing system prompt and append
            existing = getattr(request, "system_prompt", None) or ""
            if "Available Skills" in str(existing):
                # Already injected, return as-is
                return SystemMessage(content=str(existing))
            
            if existing:
                new_prompt = f"{existing}\n\n{injection}"
            else:
                new_prompt = injection
            
            return SystemMessage(content=new_prompt)
        
        return skills_prompt

    def _create_tools_middleware(self) -> Any:
        """Create middleware for tools injection using @before_model(tools=[...])."""
        tools = self.tool_factory.get_tools()
        
        # Use @before_model with tools parameter to register tools
        @_before_model(tools=tools)  # type: ignore[misc]
        def skills_tools_injector(state: Any, runtime: Any) -> None:
            """Tools are automatically injected via the tools parameter."""
            return None
        
        return skills_tools_injector

    # Legacy API for backward compatibility
    def get_prompt_middleware(self) -> Any:
        """Return the prompt middleware (legacy API)."""
        return self._create_prompt_middleware()

    def get_tools_middleware(self, base_tools: Optional[List[BaseTool]] = None) -> Any:
        """Return the tools middleware (legacy API)."""
        return self._create_tools_middleware()

    def get_lifecycle_middleware(self, stop_on_exit: bool = False) -> Any:
        """Return the lifecycle middleware (legacy API)."""
        return self._create_lifecycle_middleware(stop_on_exit)

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Legacy middleware logic to inject Prompt (for manual usage).
        
        Prefer using get_middlewares() with create_deep_agent() instead.
        """
        skills = self.skill_manager.discover_skills()
        skills_text = "\n".join([f"- {s.name}: {s.description}" for s in skills])
        if not skills_text:
            skills_text = "(No skills currently available)"

        injection_content = f"""
{SKILL_GUIDE_PROMPT}

## Currently Available Skills
{skills_text}
"""
        
        # Case A: 'system_prompt' string in state
        if "system_prompt" in state and isinstance(state["system_prompt"], str):
             state["system_prompt"] += f"\n\n{injection_content}"
             return state

        # Case B: 'messages' list in state (LangGraph / Chat Models)
        if "messages" in state:
            messages = state["messages"]
            system_msg_idx = -1
            for i, msg in enumerate(messages):
                if isinstance(msg, SystemMessage):
                    system_msg_idx = i
                    break
            
            if system_msg_idx >= 0:
                original = messages[system_msg_idx].content
                if "Available Skills" not in str(original):
                    new_content = str(original) + f"\n\n{injection_content}"
                    messages[system_msg_idx] = SystemMessage(content=new_content)
            else:
                messages.insert(0, SystemMessage(content=injection_content))
                
        return state

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Allow calling the instance directly as a callable (legacy API)."""
        return self.process(state)

    def close(self, remove_container: bool = False):
        """Explicitly stop/cleanup runner container."""
        try:
            self.runner.stop(remove=remove_container)
        except Exception:
            pass


# Export for convenience
__all__ = ["SkillsMiddleware"]
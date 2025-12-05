from typing import Any, Dict, List, Optional
from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool

from agent_skills.core.skill_manager import SkillManager
from agent_skills.core.docker_runner import DockerRunner
from agent_skills.core.tools_factory import DockerToolFactory
from agent_skills.mcp.prompts import SKILL_GUIDE_PROMPT

class DockerSkillsMiddleware:
    """
    LangChain Middleware that provides Agent Skills via Docker-isolated execution.
    
    Features:
    - Injects 'skills_*' tools into the agent.
    - Injects Skill Guide and Available Skills list into System Prompt.
    - Manages a background Docker container for safe execution.
    """

    def __init__(
        self, 
        workspace_dir: str, 
        skills_dir: Optional[str] = None
    ):
        """
        Initialize the middleware.
        
        Args:
            workspace_dir: Local path to the user's workspace (will be mounted to /workspace)
            skills_dir: Local path to custom skills (will be mounted/visible)
        """
        self.workspace_dir = Path(workspace_dir).resolve()
        
        # Determine skills dir
        # If provided, use it. If not, use built-in.
        # Note: SkillManager handles defaults, but we need a path for Docker mounting.
        # DockerRunner expects a single 'skills_dir' mount point usually, 
        # but SkillManager can handle multiple.
        # For simplicity in this implementation, we assume one primary skills dir 
        # or we rely on the default structure.
        
        # Let's see where default skills are.
        default_skills = Path(__file__).parent.parent / "skills"
        self.skills_dir = Path(skills_dir).resolve() if skills_dir else default_skills
        
        # Initialize Runner
        self.runner = DockerRunner()
        # Start container immediately
        self.runner.start(str(self.workspace_dir), str(self.skills_dir))
        
        # Initialize Manager (for discovery)
        self.skill_manager = SkillManager(
            skills_dirs=[self.skills_dir] if skills_dir else None,
            builtin_skills_dir=default_skills
        )
        
        # Initialize Tool Factory
        self.tool_factory = DockerToolFactory(
            runner=self.runner,
            skill_manager=self.skill_manager,
            host_workspace=self.workspace_dir,
            host_skills=self.skills_dir
        )

    def get_tools(self) -> List[BaseTool]:
        """Return the list of Docker-backed tools."""
        return self.tool_factory.get_tools()

    def get_prompt(self) -> str:
        """
        Get the complete skill system prompt (SKILL_GUIDE_PROMPT + Available Skills).
        Use this when you need to include the prompt at agent creation time.
        """
        skills = self.skill_manager.discover_skills()
        skills_text = "\n".join([f"- {s.name}: {s.description}" for s in skills])
        if not skills_text:
            skills_text = "(No skills currently available)"

        return f"""
{SKILL_GUIDE_PROMPT}

## Currently Available Skills
{skills_text}
"""

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Middleware logic to inject Prompt.
        Call this in your agent loop or use as a RunnableBinding if supported.
        
        Example for LangGraph:
        def middleware_node(state):
            return middleware.process(state)
        """
        # 1. Discover Skills
        skills = self.skill_manager.discover_skills()
        skills_text = "\n".join([f"- {s.name}: {s.description}" for s in skills])
        if not skills_text:
            skills_text = "(No skills currently available)"

        # 2. Construct Injection
        injection_content = f"""
{SKILL_GUIDE_PROMPT}

## Currently Available Skills
{skills_text}
"""
        
        # 3. Inject into State
        # Support multiple state formats
        
        # Case A: 'system_prompt' string in state (Common in simple agents)
        if "system_prompt" in state and isinstance(state["system_prompt"], str):
             state["system_prompt"] += f"\n\n{injection_content}"
             return state

        # Case B: 'messages' list in state (LangGraph / Chat Models)
        if "messages" in state:
            messages = state["messages"]
            # Look for SystemMessage
            system_msg_idx = -1
            for i, msg in enumerate(messages):
                if isinstance(msg, SystemMessage):
                    system_msg_idx = i
                    break
            
            if system_msg_idx >= 0:
                # Append to existing
                original = messages[system_msg_idx].content
                # Check if already injected to avoid dupes in loops?
                # Simple check: if "Available Skills" not in original
                if "Available Skills" not in str(original):
                    new_content = str(original) + f"\n\n{injection_content}"
                    messages[system_msg_idx] = SystemMessage(content=new_content)
            else:
                # Insert new SystemMessage
                messages.insert(0, SystemMessage(content=injection_content))
                
        return state

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Allow calling the instance directly as a callable."""
        return self.process(state)


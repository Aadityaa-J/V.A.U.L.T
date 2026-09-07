from typing import Any, Dict, List, Optional

from agents.agent_loop import AgentLoop
from models.router import select_model


class BaseAgent:
    """
    Base class for all V.A.U.L.T. agents.

    Responsibilities:

    - Select the appropriate model.
    - Preserve the agent system prompt.
    - Pass conversation history to AgentLoop.
    - Configure tools and maximum reasoning steps.
    """

    def __init__(
        self,
        name: str,
        task_type: str,
        system_prompt: str,
        tools=None,
        max_steps: int = 5,
    ):
        self.name = name
        self.task_type = task_type
        self.system_prompt = system_prompt
        self.tools = tools or {}
        self.max_steps = max_steps

    def run(
        self,
        task: str,
        conversation_history: Optional[
            List[Dict[str, Any]]
        ] = None,
    ) -> str:
        """
        Run the agent using the appropriate model.

        Conversation history is preserved and passed to
        AgentLoop so the loop can build a proper
        multi-message conversation for the LLM.
        """

        if not isinstance(task, str):
            raise TypeError(
                "Task must be a string."
            )

        if not task.strip():
            raise ValueError(
                "Task cannot be empty."
            )

        # ---------------------------------------------
        # MODEL TASK TYPE
        # ---------------------------------------------

        model_task_type = (
            self._get_model_task_type()
        )

        # ---------------------------------------------
        # SMART MODEL SELECTION
        # ---------------------------------------------

        model = select_model(
            model_task_type
        )

        # ---------------------------------------------
        # CREATE AGENT LOOP
        # ---------------------------------------------

        loop = AgentLoop(
            system_prompt=self.system_prompt,
            model=model,
            tools=self.tools,
            max_steps=self.max_steps,
        )

        # ---------------------------------------------
        # RUN AGENT
        # ---------------------------------------------

        return loop.run(
            task=task,
            conversation_history=conversation_history,
        )

    def _get_model_task_type(self) -> str:
        """
        Map agent task types directly to supported
        V.A.U.L.T. router task types.

        This allows SmartModelSelector to select models
        based on the actual capabilities required.
        """

        task_type_mapping = {

            # Document Agent
            "document": "document",

            # Coding Agent
            "coding": "coding",

            # Engineering Agent
            "engineering": "engineering",

            # General Agent
            "general": "simple",

        }

        return task_type_mapping.get(
            self.task_type,
            "simple",
        )
from agents.agent_loop import AgentLoop
from models.router import select_model


class BaseAgent:
    def __init__(
        self,
        name: str,
        task_type: str,
        system_prompt: str,
        tools=None,
        max_steps: int = 5
    ):
        self.name = name
        self.task_type = task_type
        self.system_prompt = system_prompt
        self.tools = tools or {}
        self.max_steps = max_steps

    def run(
        self,
        task: str,
        conversation_history=None
    ) -> str:
        """
        Run the agent using the appropriate model.
        """

        model_task_type = self._get_model_task_type()

        model = select_model(model_task_type)

        loop = AgentLoop(
            system_prompt=self.system_prompt,
            model=model,
            tools=self.tools,
            max_steps=self.max_steps
        )

        return loop.run(
            task,
            conversation_history=conversation_history
        )

    def _get_model_task_type(self) -> str:
        """
        Map agent task types to model router task types.
        """

        task_type_mapping = {
            "document": "simple",
            "coding": "complex",
            "engineering": "complex",
            "general": "simple",
        }

        return task_type_mapping.get(
            self.task_type,
            "simple"
        )
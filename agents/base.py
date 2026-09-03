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

    def run(self, task: str) -> str:
        model = select_model(self.task_type)

        loop = AgentLoop(
            system_prompt=self.system_prompt,
            model=model,
            tools=self.tools,
            max_steps=self.max_steps
        )

        return loop.run(task)
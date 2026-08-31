from agents.agent_loop import AgentLoop
from models.llm import generate
from models.router import select_model


class BaseAgent:
    def __init__(
        self,
        name: str,
        task_type: str,
        system_prompt: str | None = None,
        tools=None
    ):
        self.name = name
        self.task_type = task_type
        self.system_prompt = system_prompt
        self.tools = tools or {}

    def run(self, task: str) -> str:
        if self.tools or self.system_prompt:
            loop = AgentLoop(
                system_prompt=self.system_prompt or "",
                tools=self.tools
            )

            return loop.run(task)

        model = select_model(self.task_type)

        prompt = self.build_prompt(task)

        return generate(prompt, model)

    def build_prompt(self, task: str) -> str:
        return task
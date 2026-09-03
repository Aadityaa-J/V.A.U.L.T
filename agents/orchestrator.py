from agents.document_agent import DocumentAgent
from agents.coding_agent import CodingAgent
from agents.engineering_agent import EngineeringAgent
from agents.task_classifier import TaskClassifier
from tools.registry import ToolRegistry


class Orchestrator:
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.classifier = TaskClassifier()

        self.agents = {
            "document": DocumentAgent(),
            "coding": CodingAgent(),
            "engineering": EngineeringAgent(),
        }

        self.agent_tools = {
            "document": [
                "read_file",
                "search_knowledge",
                "analyze_image",
                "create_docx",
            ],
            "coding": [
                "read_file",
                "write_file",
                "execute_code",
            ],
            "engineering": [
                "search_knowledge",
                "calculate",
                "create_xlsx",
            ],
        }

    def register_tool(self, tool) -> None:
        self.tool_registry.register(tool)

    def _get_agent_tools(self, task_type: str):
        tool_names = self.agent_tools.get(
            task_type,
            []
        )

        tools = {}

        for name in tool_names:
            if self.tool_registry.has(name):
                tools[name] = self.tool_registry.get(name)

        return tools

    def run(self, task: str) -> str:
        task_type = self.classifier.classify(task)

        if task_type not in self.agents:
            raise ValueError(
                f"Unsupported task type: {task_type}"
            )

        agent = self.agents[task_type]

        agent.tools = self._get_agent_tools(task_type)

        return agent.run(task)
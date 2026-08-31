from agents.document_agent import DocumentAgent
from agents.coding_agent import CodingAgent
from agents.engineering_agent import EngineeringAgent


class Orchestrator:
    def __init__(self):
        self.agents = {
            "document": DocumentAgent(),
            "coding": CodingAgent(),
            "engineering": EngineeringAgent(),
        }

    def run(self, task: str, task_type: str) -> str:
        if task_type not in self.agents:
            raise ValueError(
                f"Unsupported task type: {task_type}"
            )

        agent = self.agents[task_type]

        return agent.run(task)
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentContext:
    task: str

    observations: List[Any] = field(
        default_factory=list
    )

    steps: List[Dict[str, Any]] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def add_observation(self, observation: Any) -> None:
        self.observations.append(observation)

    def add_step(
        self,
        step_number: int,
        action: Dict[str, Any],
        observation: Any = None
    ) -> None:
        self.steps.append({
            "step": step_number,
            "action": action,
            "observation": observation
        })

    def get_observations(self) -> List[Any]:
        return list(self.observations)

    def get_steps(self) -> List[Dict[str, Any]]:
        return list(self.steps)

    def set_metadata(
        self,
        key: str,
        value: Any
    ) -> None:
        self.metadata[key] = value

    def get_metadata(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        return self.metadata.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "observations": self.observations,
            "steps": self.steps,
            "metadata": self.metadata
        }
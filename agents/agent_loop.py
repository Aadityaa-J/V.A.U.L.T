from typing import Dict, Any

from models.llm import generate
from tools.base import BaseTool
from agents.context import AgentContext


class AgentLoop:
    def __init__(
        self,
        system_prompt: str,
        model: str,
        tools: Dict[str, BaseTool] | None = None,
        max_steps: int = 5
    ):
        self.system_prompt = system_prompt
        self.model = model
        self.tools = tools or {}
        self.max_steps = max_steps

        self.last_state: Dict[str, Any] = {}

    def run(self, task: str) -> str:
        context = AgentContext(task=task)

        self.last_state = context.to_dict()

        for step_number in range(
            1,
            self.max_steps + 1
        ):
            state = context.to_dict()

            prompt = self._build_prompt(state)

            response = generate(
                prompt=prompt,
                model=self.model
            )

            action = self._parse_action(response)

            if action["type"] == "final":
                context.add_step(
                    step_number=step_number,
                    action=action,
                    observation=None
                )

                self.last_state = context.to_dict()

                return action["content"]

            if action["type"] == "tool":
                if self._is_repeated_tool_call(
                    context.to_dict(),
                    action
                ):
                    result = {
                        "type": "tool_error",
                        "tool": action["name"],
                        "error": (
                            "Repeated identical tool call "
                            "detected. Execution stopped "
                            "to prevent an agent loop."
                        ),
                        "arguments": action["arguments"]
                    }

                    context.add_step(
                        step_number=step_number,
                        action=action,
                        observation=result
                    )

                    context.add_observation(result)

                    self.last_state = context.to_dict()

                    return (
                        "Agent stopped because a repeated "
                        "identical tool call was detected."
                    )

                result = self._execute_tool(
                    action["name"],
                    action["arguments"]
                )

                context.add_step(
                    step_number=step_number,
                    action=action,
                    observation=result
                )

                context.add_observation(result)

                self.last_state = context.to_dict()

            else:
                context.add_step(
                    step_number=step_number,
                    action=action,
                    observation=None
                )

                self.last_state = context.to_dict()

                return response

        self.last_state = context.to_dict()

        return (
            "Agent stopped because the maximum "
            "number of steps was reached."
        )

    def _build_prompt(self, state: Dict[str, Any]) -> str:
        observations = "\n".join(
            str(item)
            for item in state["observations"]
        )

        available_tools = "\n".join(
            f"- {tool.name}: {tool.description}"
            for tool in self.tools.values()
        )

        return f"""
{self.system_prompt}

You are operating in an agentic loop.

User task:
{state["task"]}

Previous observations:
{observations if observations else "None"}

Available tools:
{available_tools if available_tools else "None"}

Decide what to do next.

If you need to use a tool, respond exactly as:

ACTION: tool
NAME: <tool name>
ARGUMENTS: <argument>

If you have enough information to answer, respond exactly as:

ACTION: final
CONTENT: <final answer>
"""

    def _parse_action(self, response: str) -> Dict[str, Any]:
        """
        Parse the model response into a structured action.

        Supported actions:

        ACTION: final
        CONTENT: <answer>

        ACTION: tool
        NAME: <tool name>
        ARGUMENTS: <arguments>
        """

        lines = [
            line.strip()
            for line in response.splitlines()
            if line.strip()
        ]

        action_type = None
        name = ""
        arguments = ""
        content = ""

        for line in lines:
            if line.upper().startswith("ACTION:"):
                action_value = line.split(
                    ":",
                    1
                )[1].strip().lower()

                if action_value == "final":
                    action_type = "final"

                elif action_value == "tool":
                    action_type = "tool"

            elif line.upper().startswith("NAME:"):
                name = line.split(
                    ":",
                    1
                )[1].strip()

            elif line.upper().startswith("ARGUMENTS:"):
                arguments = line.split(
                    ":",
                    1
                )[1].strip()

            elif line.upper().startswith("CONTENT:"):
                content = line.split(
                    ":",
                    1
                )[1].strip()

        if action_type == "final":
            return {
                "type": "final",
                "content": content
            }

        if action_type == "tool":
            return {
                "type": "tool",
                "name": name,
                "arguments": arguments
            }

        return {
            "type": "unknown",
            "content": response
        }

    def _is_repeated_tool_call(
        self,
        state: Dict[str, Any],
        action: Dict[str, Any]
    ) -> bool:

        for step in state["steps"]:
            previous_action = step["action"]

            if previous_action.get("type") != "tool":
                continue

            if (
                previous_action.get("name")
                == action.get("name")
                and
                previous_action.get("arguments")
                == action.get("arguments")
            ):
                return True

        return False

    def _execute_tool(
        self,
        name: str,
        arguments: str
    ) -> Any:

        if name not in self.tools:
            return {
                "type": "tool_error",
                "tool": name,
                "error": "Tool is not available.",
                "arguments": arguments
            }

        tool = self.tools[name]

        try:
            result = tool.execute(arguments)

            return {
                "type": "tool_result",
                "tool": name,
                "result": result
            }

        except Exception as exc:
            return {
                "type": "tool_error",
                "tool": name,
                "error": str(exc),
                "arguments": arguments
            }
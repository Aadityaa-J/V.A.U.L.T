from typing import Callable, Dict, Any

from models.llm import generate


class AgentLoop:
    def __init__(
        self,
        system_prompt: str,
        tools: Dict[str, Callable] | None = None,
        max_steps: int = 5
    ):
        self.system_prompt = system_prompt
        self.tools = tools or {}
        self.max_steps = max_steps

    def run(self, task: str) -> str:
        state: Dict[str, Any] = {
            "task": task,
            "observations": [],
            "steps": []
        }

        for _ in range(self.max_steps):
            prompt = self._build_prompt(state)

            response = generate(
                prompt=prompt
            )

            action = self._parse_action(response)

            if action["type"] == "final":
                return action["content"]

            if action["type"] == "tool":
                result = self._execute_tool(
                    action["name"],
                    action["arguments"]
                )

                state["steps"].append({
                    "action": action,
                    "observation": result
                })

                state["observations"].append(result)

            else:
                return response

        return "Agent stopped because the maximum number of steps was reached."

    def _build_prompt(self, state: Dict[str, Any]) -> str:
        observations = "\n".join(
            str(item)
            for item in state["observations"]
        )

        return f"""
{self.system_prompt}

You are operating in an agentic loop.

User task:
{state["task"]}

Previous observations:
{observations if observations else "None"}

Available tools:
{", ".join(self.tools.keys()) if self.tools else "None"}

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
        if "ACTION: final" in response:
            content = response.split(
                "CONTENT:",
                1
            )[1].strip()

            return {
                "type": "final",
                "content": content
            }

        if "ACTION: tool" in response:
            lines = response.splitlines()

            name = ""
            arguments = ""

            for line in lines:
                if line.startswith("NAME:"):
                    name = line.split(
                        "NAME:",
                        1
                    )[1].strip()

                elif line.startswith("ARGUMENTS:"):
                    arguments = line.split(
                        "ARGUMENTS:",
                        1
                    )[1].strip()

            return {
                "type": "tool",
                "name": name,
                "arguments": arguments
            }

        return {
            "type": "unknown",
            "content": response
        }

    def _execute_tool(
        self,
        name: str,
        arguments: str
    ) -> Any:

        if name not in self.tools:
            return f"Tool '{name}' is not available."

        try:
            return self.tools[name](arguments)
        except Exception as exc:
            return f"Tool execution failed: {exc}"
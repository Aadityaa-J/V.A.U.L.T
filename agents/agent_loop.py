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

    def run(
        self,
        task: str,
        conversation_history=None
    ) -> str:
        """
        Run the agent loop.

        conversation_history contains previous user and
        assistant messages supplied by the session system.
        """

        context = AgentContext(task=task)

        self.last_state = context.to_dict()

        for step_number in range(
            1,
            self.max_steps + 1
        ):
            state = context.to_dict()

            prompt = self._build_prompt(
                state,
                conversation_history
            )

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

                continue

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

    def _build_prompt(
        self,
        state: Dict[str, Any],
        conversation_history=None
    ) -> str:
        """
        Build the prompt for the LLM.
        """

        observations = "\n".join(
            str(item)
            for item in state["observations"]
        )

        available_tools = "\n".join(
            f"- {tool.name}: {tool.description}"
            for tool in self.tools.values()
        )

        history_lines = []

        if conversation_history:
            for message in conversation_history:
                role = message.get(
                    "role",
                    "unknown"
                )

                content = message.get(
                    "content",
                    ""
                )

                history_lines.append(
                    f"{role.capitalize()}: {content}"
                )

        conversation_text = "\n".join(
            history_lines
        )

        if not conversation_text:
            conversation_text = "None"

        return f"""
{self.system_prompt}

You are operating in an agentic loop.

Previous conversation:
{conversation_text}

Current user task:
{state["task"]}

Previous observations:
{observations if observations else "None"}

Available tools:
{available_tools if available_tools else "None"}

Decide what to do next.

IMPORTANT RESPONSE FORMAT:

If you need to use a tool:

ACTION: tool
NAME: <tool name>
ARGUMENTS:
<arguments>

If you have enough information to answer:

ACTION: final
CONTENT:
<your complete answer>

Do not place anything before ACTION.
"""

    def _parse_action(
        self,
        response: str
    ) -> Dict[str, Any]:
        """
        Parse the model response.

        Supports multiline final answers and multiline
        tool arguments.

        Supported formats:

        ACTION: final
        CONTENT:
        <multiline answer>

        ACTION: tool
        NAME: <tool name>
        ARGUMENTS:
        <multiline arguments>
        """

        if not isinstance(response, str):
            return {
                "type": "unknown",
                "content": str(response)
            }

        cleaned_response = response.strip()

        if not cleaned_response:
            return {
                "type": "unknown",
                "content": response
            }

        lines = cleaned_response.splitlines()

        action_type = None
        name = ""
        content_lines = []
        argument_lines = []

        current_section = None

        for line in lines:
            stripped_line = line.strip()
            upper_line = stripped_line.upper()

            # ----------------------------------------------
            # ACTION
            # ----------------------------------------------

            if upper_line.startswith("ACTION:"):
                action_value = (
                    stripped_line
                    .split(":", 1)[1]
                    .strip()
                    .lower()
                )

                if action_value == "final":
                    action_type = "final"

                elif action_value == "tool":
                    action_type = "tool"

                current_section = None
                continue

            # ----------------------------------------------
            # TOOL NAME
            # ----------------------------------------------

            if upper_line.startswith("NAME:"):
                name = (
                    stripped_line
                    .split(":", 1)[1]
                    .strip()
                )

                current_section = "name"
                continue

            # ----------------------------------------------
            # ARGUMENTS
            # ----------------------------------------------

            if upper_line.startswith("ARGUMENTS:"):
                argument_value = (
                    line.split(":", 1)[1]
                )

                current_section = "arguments"

                if argument_value.strip():
                    argument_lines.append(
                        argument_value.lstrip()
                    )

                continue

            # ----------------------------------------------
            # CONTENT
            # ----------------------------------------------

            if upper_line.startswith("CONTENT:"):
                content_value = (
                    line.split(":", 1)[1]
                )

                current_section = "content"

                if content_value.strip():
                    content_lines.append(
                        content_value.lstrip()
                    )

                continue

            # ----------------------------------------------
            # MULTILINE CONTENT
            # ----------------------------------------------

            if current_section == "content":
                content_lines.append(line)

            elif current_section == "arguments":
                argument_lines.append(line)

        # --------------------------------------------------
        # FINAL ACTION
        # --------------------------------------------------

        if action_type == "final":

            content = "\n".join(
                content_lines
            ).strip()

            return {
                "type": "final",
                "content": content
            }

        # --------------------------------------------------
        # TOOL ACTION
        # --------------------------------------------------

        if action_type == "tool":

            arguments = "\n".join(
                argument_lines
            ).strip()

            return {
                "type": "tool",
                "name": name,
                "arguments": arguments
            }

        # --------------------------------------------------
        # UNKNOWN RESPONSE
        # --------------------------------------------------

        return {
            "type": "unknown",
            "content": response
        }

    def _is_repeated_tool_call(
        self,
        state: Dict[str, Any],
        action: Dict[str, Any]
    ) -> bool:
        """
        Check whether the agent is attempting the exact
        same tool call again.
        """

        for step in state["steps"]:
            previous_action = step["action"]

            if previous_action.get(
                "type"
            ) != "tool":
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
        """
        Execute an available tool safely.
        """

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
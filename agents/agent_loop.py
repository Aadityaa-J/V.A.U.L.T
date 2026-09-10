from typing import Any, Dict, List, Optional
import json
import re

from models.llm import chat_generate
from tools.base import BaseTool
from agents.context import AgentContext


class AgentLoop:
    """
    Autonomous execution loop for V.A.U.L.T.

    Execution strategy:

    1. Check for deterministic tool opportunities.
    2. Execute obvious tools immediately.
    3. Otherwise use the LLM autonomous loop.

    This makes simple operations such as mathematical
    calculations significantly faster.
    """

    def __init__(
        self,
        system_prompt: str,
        model: str,
        tools: Optional[
            Dict[str, BaseTool]
        ] = None,
        max_steps: int = 5,
    ):
        self.system_prompt = system_prompt
        self.model = model
        self.tools = tools or {}
        self.max_steps = max_steps

        self.last_state: Dict[str, Any] = {}

    # ==========================================================
    # MAIN AGENT LOOP
    # ==========================================================

    def run(
        self,
        task: str,
        conversation_history=None,
    ) -> str:
        """
        Run the autonomous agent.
        """

        if not isinstance(task, str):
            raise TypeError(
                "Task must be a string."
            )

        if not task.strip():
            raise ValueError(
                "Task cannot be empty."
            )

        task = task.strip()

        # ======================================================
        # FAST PATH: DETERMINISTIC TOOL ROUTING
        # ======================================================

        direct_result = (
            self._try_direct_tool_route(
                task
            )
        )

        if direct_result is not None:
            return direct_result

        # ======================================================
        # NORMAL AUTONOMOUS AGENT LOOP
        # ======================================================

        context = AgentContext(
            task=task
        )

        # ======================================================
        # KNOWLEDGE BASE: MANDATORY FIRST RETRIEVAL
        # ======================================================
        #
        # The Document Agent has access to the semantic
        # knowledge-base tool. Do not rely solely on the LLM
        # to decide whether to call it: seed the agent loop
        # with an actual retrieval result before the model
        # gets the opportunity to answer.
        #
        # This keeps retrieval as an orchestration decision
        # rather than merely a prompt instruction.
        #
        if "search_knowledge" in self.tools:
            knowledge_result = self._execute_tool(
                "search_knowledge",
                json.dumps(
                    {
                        "query": task,
                        "top_k": 4,
                        "distance_threshold": 1.3,
                    },
                    ensure_ascii=False,
                ),
            )

            context.add_step(
                step_number=0,
                action={
                    "type": "tool",
                    "name": "search_knowledge",
                    "arguments": json.dumps(
                        {
                            "query": task,
                            "top_k": 4,
                            "distance_threshold": 1.3,
                        },
                        ensure_ascii=False,
                    ),
                },
                observation=knowledge_result,
            )

            context.add_observation(
                knowledge_result
            )

        self.last_state = context.to_dict()

        for step_number in range(
            1,
            self.max_steps + 1,
        ):

            state = context.to_dict()

            messages = self._build_messages(
                state=state,
                conversation_history=(
                    conversation_history
                ),
            )

            response = chat_generate(
                messages=messages,
                model=self.model,
                use_router=False,
            )

            action = self._parse_action(
                response
            )

            # --------------------------------------------------
            # FINAL ANSWER
            # --------------------------------------------------

            if action["type"] == "final":

                content = action.get(
                    "content",
                    ""
                ).strip()

                if not content:
                    content = response.strip()

                context.add_step(
                    step_number=step_number,
                    action=action,
                    observation=None,
                )

                self.last_state = (
                    context.to_dict()
                )

                return content

            # --------------------------------------------------
            # TOOL CALL
            # --------------------------------------------------

            if action["type"] == "tool":

                tool_name = action.get(
                    "name",
                    ""
                ).strip()

                if not tool_name:

                    error_result = {
                        "type": "tool_error",
                        "tool": None,
                        "error": (
                            "The model requested a tool "
                            "but did not provide a tool name."
                        ),
                    }

                    context.add_step(
                        step_number=step_number,
                        action=action,
                        observation=error_result,
                    )

                    context.add_observation(
                        error_result
                    )

                    self.last_state = (
                        context.to_dict()
                    )

                    continue

                # ----------------------------------------------
                # REPEATED TOOL CALL PROTECTION
                # ----------------------------------------------

                if self._is_repeated_tool_call(
                    context.to_dict(),
                    action,
                ):

                    result = {
                        "type": "tool_error",
                        "tool": tool_name,
                        "error": (
                            "Repeated identical tool call "
                            "detected. The tool was not "
                            "executed again."
                        ),
                        "arguments": action.get(
                            "arguments"
                        ),
                    }

                    context.add_step(
                        step_number=step_number,
                        action=action,
                        observation=result,
                    )

                    context.add_observation(
                        result
                    )

                    self.last_state = (
                        context.to_dict()
                    )

                    continue

                # ----------------------------------------------
                # EXECUTE TOOL
                # ----------------------------------------------

                result = self._execute_tool(
                    tool_name,
                    action.get(
                        "arguments",
                        ""
                    ),
                )

                context.add_step(
                    step_number=step_number,
                    action=action,
                    observation=result,
                )

                context.add_observation(
                    result
                )

                self.last_state = (
                    context.to_dict()
                )

                continue

            # --------------------------------------------------
            # UNKNOWN RESPONSE
            # --------------------------------------------------

            context.add_step(
                step_number=step_number,
                action=action,
                observation=None,
            )

            self.last_state = (
                context.to_dict()
            )

            return response.strip()

        # ======================================================
        # MAXIMUM STEPS REACHED
        # ======================================================

        self.last_state = context.to_dict()

        return (
            "Agent stopped because the maximum "
            "number of execution steps was reached."
        )

    # ==========================================================
    # DIRECT TOOL ROUTING
    # ==========================================================

    def _try_direct_tool_route(
        self,
        task: str,
    ) -> Optional[str]:
        """
        Detect obvious tool requests and execute them
        immediately.

        Currently supports:

        - Mathematical calculations.
        """

        # ------------------------------------------------------
        # CALCULATOR
        # ------------------------------------------------------

        expression = (
            self._extract_math_expression(
                task
            )
        )

        if expression is not None:

            if "calculate" not in self.tools:
                return None

            result = self._execute_tool(
                "calculate",
                expression,
            )

            if result["type"] == "tool_result":

                calculation_result = (
                    result["result"]
                )

                return (
                    f"{expression} = "
                    f"{calculation_result}"
                )

            return None

        return None

    # ==========================================================
    # MATH EXPRESSION EXTRACTION
    # ==========================================================

    def _extract_math_expression(
        self,
        task: str,
    ) -> Optional[str]:
        """
        Extract a simple mathematical expression.

        Examples:

            25 * 48

            Calculate 25 * 48

            What is (100 + 25) / 5?

        Returns the expression or None.
        """

        text = task.strip()

        # ------------------------------------------------------
        # REMOVE COMMON PREFIXES
        # ------------------------------------------------------

        prefixes = [
            "calculate",
            "what is",
            "solve",
            "compute",
            "evaluate",
        ]

        cleaned = text.lower()

        for prefix in prefixes:

            if cleaned.startswith(prefix):

                text = text[
                    len(prefix):
                ].strip(
                    " :?"
                )

                break

        # ------------------------------------------------------
        # REMOVE QUESTION MARK
        # ------------------------------------------------------

        text = text.strip()

        if text.endswith("?"):

            text = text[:-1].strip()

        # ------------------------------------------------------
        # NORMALIZE COMMON SYMBOLS
        # ------------------------------------------------------

        text = (
            text
            .replace("×", "*")
            .replace("÷", "/")
        )

        # ------------------------------------------------------
        # VALIDATE MATH EXPRESSION
        # ------------------------------------------------------

        if not text:
            return None

        pattern = (
            r"^[0-9+\-*/%.()\s]+$"
        )

        if re.fullmatch(
            pattern,
            text,
        ):

            return text

        return None

    # ==========================================================
    # MESSAGE BUILDING
    # ==========================================================

    def _build_messages(
        self,
        state: Dict[str, Any],
        conversation_history=None,
    ) -> List[Dict[str, str]]:

        messages: List[
            Dict[str, str]
        ] = []

        # ------------------------------------------------------
        # MAIN SYSTEM PROMPT
        # ------------------------------------------------------

        system_content = (
            f"{self.system_prompt}\n\n"

            "You are operating inside the "
            "V.A.U.L.T. autonomous agent system.\n\n"

            "You must decide whether you need a tool "
            "before answering.\n\n"

            "IMPORTANT RESPONSE FORMAT\n\n"

            "If you need to use a tool, respond EXACTLY "
            "in this structure:\n\n"

            "ACTION: tool\n"
            "NAME: <tool name>\n"
            "ARGUMENTS:\n"
            "<tool arguments>\n\n"

            "If a tool requires multiple parameters, "
            "use JSON:\n\n"

            "ACTION: tool\n"
            "NAME: <tool name>\n"
            "ARGUMENTS:\n"
            "{\"parameter\": \"value\"}\n\n"

            "If you already have enough information "
            "to answer the user:\n\n"

            "ACTION: final\n"
            "CONTENT:\n"
            "<complete answer>\n\n"

            "Rules:\n"
            "- Do not place anything before ACTION.\n"
            "- Use only available tools.\n"
            "- After receiving a tool result, use that "
            "result when answering.\n"
            "- Do not repeat an identical tool call.\n"
            "- Do not invent tool results.\n"
            "- If no tool is necessary, answer directly."
        )

        messages.append(
            {
                "role": "system",
                "content": system_content,
            }
        )

        # ------------------------------------------------------
        # CONVERSATION HISTORY
        # ------------------------------------------------------

        if conversation_history:

            for message in conversation_history:

                if not isinstance(
                    message,
                    dict,
                ):
                    continue

                role = message.get(
                    "role"
                )

                content = message.get(
                    "content",
                    ""
                )

                if role not in {
                    "system",
                    "user",
                    "assistant",
                }:
                    continue

                if not isinstance(
                    content,
                    str,
                ):
                    continue

                if not content.strip():
                    continue

                messages.append(
                    {
                        "role": role,
                        "content": content.strip(),
                    }
                )

        # ------------------------------------------------------
        # AVAILABLE TOOLS
        # ------------------------------------------------------

        if self.tools:

            available_tools = []

            for tool in self.tools.values():

                available_tools.append(
                    f"- NAME: {tool.name}\n"
                    f"  DESCRIPTION: "
                    f"{tool.description}"
                )

            messages.append(
                {
                    "role": "system",
                    "content": (
                        "AVAILABLE TOOLS:\n\n"
                        + "\n\n".join(
                            available_tools
                        )
                    ),
                }
            )

        else:

            messages.append(
                {
                    "role": "system",
                    "content": (
                        "No tools are available for "
                        "this agent."
                    ),
                }
            )

        # ------------------------------------------------------
        # TOOL OBSERVATIONS
        # ------------------------------------------------------

        observations = state.get(
            "observations",
            [],
        )

        if observations:

            observation_blocks = []

            for index, observation in enumerate(
                observations,
                start=1,
            ):

                observation_text = (
                    self._format_observation(
                        observation
                    )
                )

                observation_blocks.append(
                    f"Observation {index}:\n"
                    f"{observation_text}"
                )

            messages.append(
                {
                    "role": "system",
                    "content": (
                        "TOOL RESULTS:\n\n"
                        + "\n\n".join(
                            observation_blocks
                        )
                        + "\n\n"
                        "Use the tool results above as "
                        "real observations from the system."
                    ),
                }
            )

        # ------------------------------------------------------
        # CURRENT TASK
        # ------------------------------------------------------

        messages.append(
            {
                "role": "user",
                "content": state["task"],
            }
        )

        return messages

    # ==========================================================
    # ACTION PARSER
    # ==========================================================

    def _parse_action(
        self,
        response: str,
    ) -> Dict[str, Any]:

        if not isinstance(response, str):

            return {
                "type": "unknown",
                "content": str(response),
            }

        cleaned_response = response.strip()

        if not cleaned_response:

            return {
                "type": "unknown",
                "content": "",
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

            # --------------------------------------------------
            # ACTION
            # --------------------------------------------------

            if upper_line.startswith(
                "ACTION:"
            ):

                action_value = (
                    stripped_line
                    .split(
                        ":",
                        1,
                    )[1]
                    .strip()
                )

                action_value_lower = action_value.lower()

                if action_value_lower == "final":

                    action_type = "final"

                elif action_value_lower == "tool":

                    action_type = "tool"

                elif action_value in self.tools:

                    # Accept the shorthand emitted by some
                    # local models:
                    #
                    # ACTION: file_exists
                    #
                    # instead of:
                    #
                    # ACTION: tool
                    # NAME: file_exists

                    action_type = "tool"
                    name = action_value

                else:

                    # Case-insensitive fallback for tool names.
                    for tool_name in self.tools:

                        if (
                            tool_name.lower()
                            == action_value_lower
                        ):

                            action_type = "tool"
                            name = tool_name
                            break

                current_section = None

                continue

            # --------------------------------------------------
            # NAME
            # --------------------------------------------------

            if upper_line.startswith(
                "NAME:"
            ):

                name = (
                    stripped_line
                    .split(
                        ":",
                        1,
                    )[1]
                    .strip()
                )

                current_section = "name"

                continue

            # --------------------------------------------------
            # ARGUMENTS
            # --------------------------------------------------

            if upper_line.startswith(
                "ARGUMENTS:"
            ):

                argument_value = (
                    line
                    .split(
                        ":",
                        1,
                    )[1]
                )

                current_section = "arguments"

                if argument_value.strip():

                    argument_lines.append(
                        argument_value.lstrip()
                    )

                continue

            # --------------------------------------------------
            # CONTENT
            # --------------------------------------------------

            if upper_line.startswith(
                "CONTENT:"
            ):

                content_value = (
                    line
                    .split(
                        ":",
                        1,
                    )[1]
                )

                current_section = "content"

                if content_value.strip():

                    content_lines.append(
                        content_value.lstrip()
                    )

                continue

            # --------------------------------------------------
            # MULTILINE SECTIONS
            # --------------------------------------------------

            if current_section == "content":

                content_lines.append(line)

            elif current_section == "arguments":

                argument_lines.append(line)

        # ------------------------------------------------------
        # FINAL
        # ------------------------------------------------------

        if action_type == "final":

            content = "\n".join(
                content_lines
            ).strip()

            return {
                "type": "final",
                "content": content,
            }

        # ------------------------------------------------------
        # TOOL
        # ------------------------------------------------------

        if action_type == "tool":

            arguments = "\n".join(
                argument_lines
            ).strip()

            return {
                "type": "tool",
                "name": name,
                "arguments": arguments,
            }

        # ------------------------------------------------------
        # UNKNOWN
        # ------------------------------------------------------

        return {
            "type": "unknown",
            "content": response,
        }

    # ==========================================================
    # REPEATED TOOL CALL DETECTION
    # ==========================================================

    def _is_repeated_tool_call(
        self,
        state: Dict[str, Any],
        action: Dict[str, Any],
    ) -> bool:

        previous_steps = state.get(
            "steps",
            [],
        )

        action_name = (
            action.get(
                "name",
                ""
            )
            .strip()
            .lower()
        )

        action_arguments = (
            self._normalize_arguments(
                action.get(
                    "arguments",
                    ""
                )
            )
        )

        for step in previous_steps:

            previous_action = step.get(
                "action",
                {}
            )

            if previous_action.get(
                "type"
            ) != "tool":

                continue

            previous_name = (
                previous_action.get(
                    "name",
                    ""
                )
                .strip()
                .lower()
            )

            previous_arguments = (
                self._normalize_arguments(
                    previous_action.get(
                        "arguments",
                        ""
                    )
                )
            )

            if (
                previous_name == action_name
                and previous_arguments
                == action_arguments
            ):

                return True

        return False

    # ==========================================================
    # ARGUMENT NORMALIZATION
    # ==========================================================

    def _normalize_arguments(
        self,
        arguments: Any,
    ) -> str:

        if arguments is None:
            return ""

        if not isinstance(
            arguments,
            str,
        ):
            return str(arguments)

        cleaned = arguments.strip()

        if not cleaned:
            return ""

        try:

            parsed = json.loads(
                cleaned
            )

            return json.dumps(
                parsed,
                sort_keys=True,
                ensure_ascii=False,
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ):

            return cleaned

    # ==========================================================
    # TOOL EXECUTION
    # ==========================================================

    def _execute_tool(
        self,
        name: str,
        arguments: Any,
    ) -> Dict[str, Any]:

        if name not in self.tools:

            return {
                "type": "tool_error",
                "tool": name,
                "error": (
                    f"Tool '{name}' is not available "
                    "to this agent."
                ),
                "arguments": arguments,
            }

        tool = self.tools[name]

        # ------------------------------------------------------
        # NORMALIZE ARGUMENTS
        # ------------------------------------------------------

        if arguments is None:

            normalized_arguments = ""

        elif isinstance(
            arguments,
            str,
        ):

            normalized_arguments = (
                arguments.strip()
            )

        else:

            try:

                normalized_arguments = (
                    json.dumps(
                        arguments
                    )
                )

            except TypeError:

                normalized_arguments = str(
                    arguments
                )

        # ------------------------------------------------------
        # EXECUTE
        # ------------------------------------------------------

        try:

            result = tool.execute(
                normalized_arguments
            )

            return {
                "type": "tool_result",
                "tool": name,
                "arguments": (
                    normalized_arguments
                ),
                "result": result,
            }

        except Exception as exc:

            return {
                "type": "tool_error",
                "tool": name,
                "arguments": (
                    normalized_arguments
                ),
                "error": str(exc),
            }

    # ==========================================================
    # OBSERVATION FORMATTER
    # ==========================================================

    def _format_observation(
        self,
        observation: Any,
    ) -> str:

        if observation is None:

            return "No observation."

        if isinstance(
            observation,
            str,
        ):

            return observation

        try:

            return json.dumps(
                observation,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        except (
            TypeError,
            ValueError,
        ):

            return str(
                observation
            )
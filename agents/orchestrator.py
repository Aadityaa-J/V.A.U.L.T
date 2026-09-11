"""
V.A.U.L.T. Main Orchestrator

Coordinates:

    - Agents
    - Tools
    - Session memory
    - Persistent memory
    - Validation
    - Fine-tuning integration
"""


import re

from agents.document_agent import DocumentAgent
from agents.coding_agent import CodingAgent
from agents.engineering_agent import EngineeringAgent
from agents.general_agent import GeneralAgent
from agents.task_classifier import TaskClassifier
from agents.session import AgentSession
from agents.memory import AgentMemory
from agents.memory_manager import MemoryManager
from agents.validation_loop import ValidationLoop


from tools.registry import ToolRegistry

from tools.adapters import (
    CalculateTool,
    RunPythonTool,
    ListFilesTool,
    ListDirectoryTool,
    FileExistsTool,
    CreateDirectoryTool,
    CopyFileTool,
    MoveFileTool,
    ReadDocumentTool,
    DocumentInfoTool,
    SearchDocumentTool,
    DocumentSummaryTool,
    SearchKnowledgeTool,
    CurrentDateTimeTool,
)


from models.fine_tuning.integration import (
    FineTuningIntegration,
)


# ==========================================================
# ORCHESTRATOR
# ==========================================================

class Orchestrator:

    """
    Main coordinator for the V.A.U.L.T. AI system.

    Responsibilities:

        - Manage agents
        - Manage conversation memory
        - Manage persistent memory
        - Assign tools
        - Route tasks
        - Run validation
        - Collect successful interactions
        - Feed fine-tuning training data

    IMPORTANT:

    Fine-tuning failures must NEVER crash the
    main V.A.U.L.T. assistant.
    """

    def __init__(
        self,
        validation_loop=None,
        fine_tuning_integration=None,
    ):

        # --------------------------------------------------
        # CORE SYSTEMS
        # --------------------------------------------------

        self.tool_registry = ToolRegistry()

        self.classifier = TaskClassifier()

        # Temporary conversation memory.

        self.session = AgentSession()

        # Persistent user memory.

        self.memory = AgentMemory()

        # Automatic memory extraction.

        self.memory_manager = MemoryManager(
            self.memory
        )

        # Validation system.

        self.validation_loop = (

            validation_loop

            or

            ValidationLoop()

        )

        # --------------------------------------------------
        # FINE-TUNING INTEGRATION
        # --------------------------------------------------

        # Fine-tuning integration is isolated from
        # the main assistant.

        self.fine_tuning = (

            fine_tuning_integration

            or

            FineTuningIntegration(

                auto_train=False,

                minimum_examples_before_check=5,

            )

        )

        # --------------------------------------------------
        # FINE-TUNING STATUS
        # --------------------------------------------------

        self.fine_tuning_enabled = True

        self.last_fine_tuning_result = None

        self.last_fine_tuning_error = None

        # --------------------------------------------------
        # AGENTS
        # --------------------------------------------------

        self.agents = {

            "document":

                DocumentAgent(),

            "coding":

                CodingAgent(),

            "engineering":

                EngineeringAgent(),

            "general":

                GeneralAgent(),

        }

        # --------------------------------------------------
        # REGISTER TOOLS
        # --------------------------------------------------

        self._register_default_tools()

        # --------------------------------------------------
        # AGENT TOOL PERMISSIONS
        # --------------------------------------------------

        self.agent_tools = {

            "document": [

                "read_document",

                "document_info",

                "search_document",

                "document_summary",

                "search_knowledge",

                "list_files",

                "list_directory",

                "file_exists",

            ],

            "coding": [

                "run_python",

                "read_document",

                "list_files",

                "list_directory",

                "file_exists",

                "create_directory",

                "copy_file",

                "move_file",

            ],

            "engineering": [

                "calculate",

                "read_document",

                "document_info",

                "search_document",

                "document_summary",

                "search_knowledge",

            ],

            "general": [],

        }

        # --------------------------------------------------
        # VALIDATION POLICY
        # --------------------------------------------------

        self.validation_required = {

            "document": True,

            "coding": True,

            "engineering": True,

            "general": False,

        }


    # ======================================================
    # REGISTER DEFAULT TOOLS
    # ======================================================

    def _register_default_tools(
        self
    ) -> None:

        """
        Register all currently available
        V.A.U.L.T. tools.
        """

        default_tools = [

            # Calculation

            CalculateTool(),

            # Python execution

            RunPythonTool(),

            # File tools

            ListFilesTool(),

            ListDirectoryTool(),

            FileExistsTool(),

            CreateDirectoryTool(),

            CopyFileTool(),

            MoveFileTool(),

            # Document tools

            ReadDocumentTool(),

            DocumentInfoTool(),

            SearchDocumentTool(),

            DocumentSummaryTool(),

            SearchKnowledgeTool(),
            CurrentDateTimeTool(),

        ]

        for tool in default_tools:

            self.tool_registry.register(
                tool
            )


    # ======================================================
    # REGISTER TOOL
    # ======================================================

    def register_tool(
        self,
        tool
    ) -> None:

        """
        Dynamically register an additional tool.
        """

        self.tool_registry.register(
            tool
        )


    # ======================================================
    # GET AGENT TOOLS
    # ======================================================

    def _get_agent_tools(
        self,
        task_type: str,
        task: str = "",
        user_id=None,
    ) -> dict:
        """
        Return the tools allowed for this specific request.

        Tool access is task-aware rather than globally enabled. In
        particular, semantic RAG is attached only when the request
        explicitly indicates that internal/organizational knowledge is
        required. This prevents ordinary conversation, coding, and
        calculations from being routed through the knowledge base.
        """

        tool_names = list(self.agent_tools.get(task_type, []))

        # RAG is an opt-in orchestration decision.
        if self._requires_knowledge(task):
            tool_names.append("search_knowledge")

        # Date/time is another deterministic capability enabled only when
        # the request actually asks for current temporal information.
        if self._requires_current_datetime(task):
            tool_names.append("get_current_datetime")

        tools = {}
        for name in tool_names:
            if not self.tool_registry.has(name):
                continue

            # SearchKnowledgeTool carries request-scoped authorization.
            if name == "search_knowledge":
                tools[name] = SearchKnowledgeTool(user_id=user_id)
            else:
                tools[name] = self.tool_registry.get(name)

        return tools

    def _looks_like_coding_task(self, task: str) -> bool:
        """Return True for clear software/code-generation requests.

        This is deliberately a routing heuristic, not a replacement for the
        TaskClassifier. Its only purpose is to guarantee that an explicit
        coding request receives the CodingAgent and its coding tools.
        """

        if not isinstance(task, str):
            return False

        text = task.strip().lower()
        if not text:
            return False

        strong_phrases = (
            "write a python",
            "write python",
            "python function",
            "python code",
            "python script",
            "write code",
            "generate code",
            "create code",
            "implement this",
            "implement a ",
            "debug this code",
            "fix this code",
            "review this code",
            "run this code",
            "execute this code",
            "test this code",
            "programming",
            "coding task",
        )
        if any(phrase in text for phrase in strong_phrases):
            return True

        # Short technical prompts containing an explicit programming
        # language or source-code vocabulary are also routed to CodingAgent.
        language_markers = (
            "python", "javascript", "typescript", "java", "c++",
            "c#", "golang", "rust", "kotlin", "swift", "sql",
        )
        code_markers = (
            "function", "class", "method", "script", "variable",
            "exception", "stack trace", "syntax error", "regex",
            "algorithm", "api endpoint", "program", "code",
        )

        has_language = any(marker in text for marker in language_markers)
        has_code_marker = any(marker in text for marker in code_markers)
        return has_language and has_code_marker

    def _requires_knowledge(self, task: str) -> bool:
        """
        Decide whether the request explicitly requires internal knowledge.

        This is intentionally conservative. It is better to leave RAG
        disabled for an ordinary question than to inject unrelated
        organizational context into the model.
        """

        if not isinstance(task, str):
            return False

        text = task.strip().lower()
        if not text:
            return False

        explicit_phrases = (
            "according to our",
            "according to the company",
            "according to the organization",
            "according to vault",
            "from our documents",
            "from our document",
            "from company documents",
            "from the knowledge base",
            "from our knowledge base",
            "search the knowledge base",
            "check the knowledge base",
            "use the knowledge base",
            "internal documentation",
            "internal document",
            "internal documents",
            "company documentation",
            "company document",
            "company documents",
            "organizational documentation",
            "organization documents",
            "our sop",
            "the sop",
            "maintenance sop",
            "inspection sop",
            "our manual",
            "the maintenance manual",
            "our records",
            "internal records",
            "our records",
        )

        if any(phrase in text for phrase in explicit_phrases):
            return True

        # Explicit knowledge-base wording is also accepted in compact form.
        tokens = set(re.findall(r"\b[a-z0-9_-]+\b", text))
        if {"kb", "knowledgebase"} & tokens:
            return True

        # Organization-specific engineering/document identifiers are useful
        # signals when users omit the words "according to our documents".
        # These patterns are deliberately narrow rather than treating every
        # technical question as an internal-knowledge query.
        internal_id_patterns = (
            r"\bpump[a-z]*[-_]?\d{2,}\b",
            r"\bvalve[a-z]*[-_]?\d{2,}\b",
            r"\bcompressor[a-z]*[-_]?\d{2,}\b",
            r"\bunit[-_]?\d{1,3}\b",
            r"\bequipment[-_]?\d{1,4}\b",
        )

        if any(re.search(pattern, text) for pattern in internal_id_patterns):
            internal_question_terms = (
                "pressure", "temperature", "vibration", "flow",
                "status", "inspection", "maintenance", "sop",
                "specification", "spec", "rating", "limit",
                "reading", "measurement", "operating", "operation",
            )
            if any(term in text for term in internal_question_terms):
                return True

        return False

    def _requires_current_datetime(self, task: str) -> bool:
        """Return True only for requests needing current date/time."""

        if not isinstance(task, str):
            return False

        text = task.strip().lower()
        phrases = (
            "what time is it",
            "current time",
            "current date",
            "today's date",
            "todays date",
            "what day is it",
            "today",
            "right now",
            "date today",
        )
        return any(phrase in text for phrase in phrases)

    # ======================================================
    # BUILD MEMORY CONTEXT
    # ======================================================

    def _build_memory_context(
        self
    ) -> dict:

        """
        Convert persistent memory into
        an LLM system message.
        """

        memory_text = (

            self.memory.to_prompt()

        )

        if not memory_text.strip():

            memory_text = (

                "No long-term user memory "
                "is currently stored."

            )

        return {

            "role":

                "system",

            "content":

                (

                    "Known long-term user memory:\n\n"

                    f"{memory_text}\n\n"

                    "Use this information only when "

                    "relevant to the user's current "

                    "request.\n"

                    "Do not randomly mention stored "

                    "facts.\n"

                    "If the user corrects previously "

                    "stored information, prioritize "

                    "the newest information."

                ),

        }


    # ======================================================
    # VALIDATION DECISION
    # ======================================================

    def _should_validate(
        self,
        task_type: str
    ) -> bool:

        """
        Determine whether a task requires
        the validation pipeline.
        """

        return (

            self.validation_required.get(

                task_type,

                False,

            )

        )


    # ======================================================
    # FINE-TUNING RECORD
    # ======================================================

    def _record_fine_tuning_interaction(
        self,
        prompt: str,
        response: str,
        task_type: str,
        successful: bool = True,
    ) -> None:

        """
        Send a completed interaction to the
        fine-tuning system.

        IMPORTANT:

        Any fine-tuning failure is isolated
        and must NEVER interrupt V.A.U.L.T.
        """

        if not self.fine_tuning_enabled:

            return

        try:

            result = (

                self.fine_tuning.record_interaction(

                    prompt=prompt,

                    response=response,

                    task_type=task_type,

                    successful=successful,

                )

            )

            self.last_fine_tuning_result = (

                result

            )

            self.last_fine_tuning_error = None

        except Exception as error:

            # Never crash V.A.U.L.T.

            self.last_fine_tuning_error = (

                str(error)

            )


    # ======================================================
    # FINE-TUNING STATUS
    # ======================================================

    def get_fine_tuning_status(
        self
    ) -> dict:

        """
        Return fine-tuning system status.
        """

        try:

            integration_status = (

                self.fine_tuning.get_status()

            )

        except Exception as error:

            integration_status = {

                "error":

                    str(error)

            }

        return {

            "enabled":

                self.fine_tuning_enabled,

            "last_result":

                self.last_fine_tuning_result,

            "last_error":

                self.last_fine_tuning_error,

            "integration":

                integration_status,

        }


    # ======================================================
    # ENABLE FINE-TUNING
    # ======================================================

    def enable_fine_tuning(
        self
    ) -> None:

        """
        Enable fine-tuning interaction collection.
        """

        self.fine_tuning_enabled = True


    # ======================================================
    # DISABLE FINE-TUNING
    # ======================================================

    def disable_fine_tuning(
        self
    ) -> None:

        """
        Disable fine-tuning interaction collection.
        """

        self.fine_tuning_enabled = False


    # ======================================================
    # SESSION HISTORY
    # ======================================================

    def get_session_history(
        self
    ):

        """
        Return the complete conversation history.
        """

        return (

            self.session.get_messages()

        )


    # ======================================================
    # MEMORY
    # ======================================================

    def get_memory(
        self
    ):

        """
        Return all persistent memory.
        """

        return (

            self.memory.get_all()

        )


    # ======================================================
    # CLEAR SESSION
    # ======================================================

    def clear_session(
        self
    ) -> None:

        """
        Clear temporary conversation history.

        Persistent memory is not affected.
        """

        self.session.clear()


    # ======================================================
    # CLEAR MEMORY
    # ======================================================

    def clear_memory(
        self
    ) -> None:

        """
        Clear persistent user memory.
        """

        self.memory.clear()


    # ======================================================
    # CLEAR ALL MEMORY
    # ======================================================

    def clear_all_memory(
        self
    ) -> None:

        """
        Clear temporary and persistent memory.
        """

        self.clear_session()

        self.clear_memory()


    # ======================================================
    # MAIN RUN
    # ======================================================

    def run(
        self,
        task: str,
        human_input=None
    ) -> str:

        """
        Process a user request.

        Flow:

            User Task
                ↓
            Memory Extraction
                ↓
            Conversation Context
                ↓
            Task Classification
                ↓
            Task-Aware Tool Routing
                ↓
            Agent Selection
                ↓
            Agent Execution
                ↓
            Validation
                ↓
            Fine-Tuning Collection
                ↓
            Store Final Response
                ↓
            Return Result
        """

        # --------------------------------------------------
        # VALIDATE INPUT
        # --------------------------------------------------

        if not isinstance(

            task,

            str,

        ):

            raise TypeError(

                "Task must be a string."

            )

        if not task.strip():

            raise ValueError(

                "Task cannot be empty."

            )

        task = task.strip()

        # --------------------------------------------------
        # AUTOMATIC MEMORY EXTRACTION
        # --------------------------------------------------

        self.memory_manager.process(

            task

        )

        # --------------------------------------------------
        # GET PREVIOUS CONVERSATION
        # --------------------------------------------------

        conversation_history = (

            self.session.get_recent_messages(

                limit=10

            )

        )

        # --------------------------------------------------
        # ADD LONG-TERM MEMORY
        # --------------------------------------------------

        memory_context = (

            self._build_memory_context()

        )

        conversation_history = [

            memory_context

        ] + conversation_history

        # --------------------------------------------------
        # STORE CURRENT USER MESSAGE
        # --------------------------------------------------

        self.session.add_user_message(

            task

        )

        # --------------------------------------------------
        # CLASSIFY TASK
        # --------------------------------------------------

        # --------------------------------------------------
        # TASK ROUTING OVERRIDE FOR OBVIOUS CODING REQUESTS
        # --------------------------------------------------
        # The classifier remains the normal routing mechanism, but an
        # explicit coding request must never fall through to the general
        # agent. This is especially important for prompts such as
        # "write a Python function..." where no company evidence is needed.
        coding_override = self._looks_like_coding_task(task)

        if coding_override:
            task_type = "coding"
        else:
            task_type = self.classifier.classify(task)

        if task_type not in self.agents:

            raise ValueError(

                f"Unsupported task type: "

                f"{task_type}"

            )

        # --------------------------------------------------
        # SELECT AGENT
        # --------------------------------------------------

        agent = (

            self.agents[

                task_type

            ]

        )

        # --------------------------------------------------
        # ASSIGN AGENT TOOLS
        # --------------------------------------------------

        request_user_id = None
        if isinstance(human_input, dict):
            request_user_id = human_input.get("user_id")

        agent.tools = self._get_agent_tools(
            task_type,
            task=task,
            user_id=request_user_id,
        )

        # --------------------------------------------------
        # RUN PRIMARY AGENT
        # --------------------------------------------------

        draft_result = (

            agent.run(

                task=task,

                conversation_history=conversation_history,

            )

        )

        # --------------------------------------------------
        # VALIDATION
        # --------------------------------------------------

        if self._should_validate(

            task_type

        ):

            validation_state = (

                self.validation_loop.run(

                    task=task,

                    initial_result=draft_result,

                    human_input=human_input,

                    task_type=task_type,

                )

            )

            result = (

                validation_state.get(

                    "final_result",

                    draft_result,

                )

            )

        else:

            result = (

                draft_result

            )

        # --------------------------------------------------
        # ENSURE RESPONSE IS VALID
        # --------------------------------------------------

        if not isinstance(

            result,

            str,

        ):

            result = str(

                result

            )

        # --------------------------------------------------
        # STORE FINAL RESPONSE
        # --------------------------------------------------

        self.session.add_assistant_message(

            result

        )

        # --------------------------------------------------
        # FINE-TUNING COLLECTION
        # --------------------------------------------------

        # This happens AFTER the final response has
        # been generated and stored.
        #
        # Fine-tuning failures cannot affect the
        # user response.

        self._record_fine_tuning_interaction(

            prompt=task,

            response=result,

            task_type=task_type,

            successful=True,

        )

        # --------------------------------------------------
        # RETURN FINAL RESPONSE
        # --------------------------------------------------

        return result


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(

        "V.A.U.L.T. ORCHESTRATOR TEST"

    )

    print("=" * 60)

    print()

    print(

        "Initializing V.A.U.L.T..."

    )

    vault = Orchestrator()

    print(

        "V.A.U.L.T. initialized successfully."

    )

    # ------------------------------------------------------
    # TEST REQUEST
    # ------------------------------------------------------

    print()

    print(

        "TEST REQUEST"

    )

    print("-" * 60)

    test_task = (

        "Calculate the force required to accelerate "

        "a 10 kg object at 5 meters per second squared."

    )

    print(

        f"USER: {test_task}"

    )

    print()

    try:

        response = (

            vault.run(

                test_task

            )

        )

        print(

            f"V.A.U.L.T.: {response}"

        )

    except Exception as error:

        print()

        print(

            "V.A.U.L.T. ERROR:"

        )

        print(

            error

        )

    # ------------------------------------------------------
    # FINE-TUNING STATUS
    # ------------------------------------------------------

    print()

    print(

        "FINE-TUNING STATUS"

    )

    print("-" * 60)

    try:

        print(

            vault.get_fine_tuning_status()

        )

    except Exception as error:

        print(

            f"Status error: {error}"

        )

    print()

    print("=" * 60)

    print(

        "ORCHESTRATOR TEST COMPLETE"

    )

    print("=" * 60)
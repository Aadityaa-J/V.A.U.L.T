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
        task_type: str
    ) -> dict:

        """
        Return the tools allowed for
        a specific agent.
        """

        tool_names = self.agent_tools.get(

            task_type,

            [],

        )

        tools = {}

        for name in tool_names:

            if self.tool_registry.has(

                name

            ):

                tools[name] = (

                    self.tool_registry.get(

                        name

                    )

                )

        return tools


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

        task_type = (

            self.classifier.classify(

                task

            )

        )

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

        agent.tools = (

            self._get_agent_tools(

                task_type

            )

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
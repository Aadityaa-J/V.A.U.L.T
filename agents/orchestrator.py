import re

from agents.document_agent import DocumentAgent
from agents.coding_agent import CodingAgent
from agents.engineering_agent import EngineeringAgent
from agents.general_agent import GeneralAgent
from agents.task_classifier import TaskClassifier
from agents.session import AgentSession
from agents.memory import AgentMemory
from agents.memory_manager import MemoryManager

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


class Orchestrator:
    def __init__(self):
        # ----------------------------------------------
        # CORE SYSTEMS
        # ----------------------------------------------

        self.tool_registry = ToolRegistry()
        self.classifier = TaskClassifier()

        # Conversation memory.
        self.session = AgentSession()

        # Persistent memory.
        self.memory = AgentMemory()

        # Automatic memory extraction.
        self.memory_manager = MemoryManager(
            self.memory
        )

        # ----------------------------------------------
        # AGENTS
        # ----------------------------------------------

        self.agents = {
            "document": DocumentAgent(),
            "coding": CodingAgent(),
            "engineering": EngineeringAgent(),
            "general": GeneralAgent(),
        }

        # ----------------------------------------------
        # TOOLS
        # ----------------------------------------------

        self._register_default_tools()

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

    def _register_default_tools(self) -> None:
        """
        Register all currently available tools.
        """

        default_tools = [
            CalculateTool(),
            RunPythonTool(),

            ListFilesTool(),
            ListDirectoryTool(),
            FileExistsTool(),
            CreateDirectoryTool(),
            CopyFileTool(),
            MoveFileTool(),

            ReadDocumentTool(),
            DocumentInfoTool(),
            SearchDocumentTool(),
            DocumentSummaryTool(),
        ]

        for tool in default_tools:
            self.tool_registry.register(tool)

    def register_tool(self, tool) -> None:
        """
        Register an additional tool dynamically.
        """

        self.tool_registry.register(tool)

    def _get_agent_tools(
        self,
        task_type: str
    ):
        """
        Return tools assigned to a particular agent.
        """

        tool_names = self.agent_tools.get(
            task_type,
            []
        )

        tools = {}

        for name in tool_names:
            if self.tool_registry.has(name):
                tools[name] = self.tool_registry.get(name)

        return tools

    def _build_memory_context(self) -> dict:
        """
        Convert persistent memory into context
        for the AI agents.
        """

        memory_text = self.memory.to_prompt()

        return {
            "role": "system",
            "content": (
                "Known long-term user memory:\n"
                f"{memory_text}\n\n"
                "Use this memory only when relevant. "
                "Do not randomly mention stored facts."
            )
        }

    def get_session_history(self):
        """
        Return the complete conversation history.
        """

        return self.session.get_messages()

    def get_memory(self):
        """
        Return all persistent memory.
        """

        return self.memory.get_all()

    def clear_session(self) -> None:
        """
        Clear temporary conversation history.
        """

        self.session.clear()

    def clear_memory(self) -> None:
        """
        Clear persistent memory.
        """

        self.memory.clear()

    def run(
        self,
        task: str
    ) -> str:
        """
        Process a user task.
        """

        if not isinstance(task, str):
            raise TypeError(
                "Task must be a string."
            )

        if not task.strip():
            raise ValueError(
                "Task cannot be empty."
            )

        # ----------------------------------------------
        # AUTOMATIC MEMORY EXTRACTION
        # ----------------------------------------------

        self.memory_manager.process(task)

        # ----------------------------------------------
        # GET PREVIOUS CONVERSATION
        # ----------------------------------------------

        conversation_history = (
            self.session.get_recent_messages(
                limit=10
            )
        )

        # ----------------------------------------------
        # ADD LONG-TERM MEMORY CONTEXT
        # ----------------------------------------------

        memory_context = (
            self._build_memory_context()
        )

        conversation_history = [
            memory_context
        ] + conversation_history

        # ----------------------------------------------
        # STORE USER MESSAGE
        # ----------------------------------------------

        self.session.add_user_message(task)

        # ----------------------------------------------
        # CLASSIFY TASK
        # ----------------------------------------------

        task_type = self.classifier.classify(task)

        if task_type not in self.agents:
            raise ValueError(
                f"Unsupported task type: "
                f"{task_type}"
            )

        agent = self.agents[task_type]

        # ----------------------------------------------
        # ASSIGN AGENT TOOLS
        # ----------------------------------------------

        agent.tools = self._get_agent_tools(
            task_type
        )

        # ----------------------------------------------
        # RUN AGENT
        # ----------------------------------------------

        result = agent.run(
            task,
            conversation_history=conversation_history
        )

        # ----------------------------------------------
        # STORE ASSISTANT RESPONSE
        # ----------------------------------------------

        self.session.add_assistant_message(
            result
        )

        return result
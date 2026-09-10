from typing import Any
import json

from tools.base import BaseTool
from tools.calculations import calculate
from tools.sandbox import run_python
from tools.system import get_current_datetime

from tools.files import (
    list_files,
    list_directory,
    file_exists,
    create_directory,
    copy_file,
    move_file,
)

from tools.documents import (
    read_document,
    document_info,
    search_document,
    get_document_summary,
)

from knowledge.search import search_knowledge


# ==========================================================
# CALCULATION TOOL
# ==========================================================

class CalculateTool(BaseTool):
    name = "calculate"

    description = (
        "Safely evaluate a mathematical expression. "
        "Example: (10 + 5) * 2"
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "Calculator arguments must be a string."
            )

        return calculate(arguments)


# ==========================================================
# PYTHON SANDBOX TOOL
# ==========================================================

class RunPythonTool(BaseTool):
    name = "run_python"

    description = (
        "Execute Python code and return stdout, stderr, "
        "success status, and return code."
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "Python code arguments must be a string."
            )

        return run_python(arguments)


# ==========================================================
# FILE TOOLS
# ==========================================================

class ListFilesTool(BaseTool):
    name = "list_files"

    description = (
        "List files in a directory. "
        "Arguments should be a directory path."
    )

    def execute(self, arguments: Any) -> Any:
        directory = (
            arguments.strip()
            if isinstance(arguments, str)
            else "."
        )

        return list_files(directory or ".")


class ListDirectoryTool(BaseTool):
    name = "list_directory"

    description = (
        "List files and directories with metadata. "
        "Arguments should be a directory path."
    )

    def execute(self, arguments: Any) -> Any:
        directory = (
            arguments.strip()
            if isinstance(arguments, str)
            else "."
        )

        return list_directory(directory or ".")


class FileExistsTool(BaseTool):
    name = "file_exists"

    description = (
        "Check whether a file exists. "
        "Arguments should be a file path."
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "File path arguments must be a string."
            )

        # ------------------------------------------------------
        # Accept both:
        #
        # D:\\path\\file.html
        #
        # and:
        #
        # {"file_path": "D:\\path\\file.html"}
        # ------------------------------------------------------

        cleaned = arguments.strip()

        if cleaned.startswith("{"):
            try:
                data = json.loads(cleaned)

                if isinstance(data, dict):
                    cleaned = data.get(
                        "file_path",
                        ""
                    )

            except json.JSONDecodeError:
                pass

        if not isinstance(cleaned, str):
            raise TypeError(
                "File path must be a string."
            )

        return file_exists(cleaned.strip())


class CreateDirectoryTool(BaseTool):
    name = "create_directory"

    description = (
        "Create a directory if it does not exist. "
        "Arguments should be a directory path."
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "Directory arguments must be a string."
            )

        return create_directory(arguments)


class CopyFileTool(BaseTool):
    name = "copy_file"

    description = (
        "Copy a file. Arguments must be JSON with "
        "'source' and 'destination' fields."
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "Copy arguments must be a JSON string."
            )

        data = json.loads(arguments)

        return copy_file(
            source=data["source"],
            destination=data["destination"],
        )


class MoveFileTool(BaseTool):
    name = "move_file"

    description = (
        "Move a file. Arguments must be JSON with "
        "'source' and 'destination' fields."
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "Move arguments must be a JSON string."
            )

        data = json.loads(arguments)

        return move_file(
            source=data["source"],
            destination=data["destination"],
        )


# ==========================================================
# DOCUMENT TOOLS
# ==========================================================

class ReadDocumentTool(BaseTool):
    name = "read_document"

    description = (
        "Read the contents of a supported document. "
        "For a document or uploaded file, use this tool "
        "when the user asks what the file says or asks "
        "you to analyze its contents. "
        "Arguments may be either a plain file path or "
        "JSON containing a 'file_path' field."
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "Document path arguments must be a string."
            )

        cleaned = arguments.strip()

        # ------------------------------------------------------
        # Accept:
        #
        # D:\\path\\file.html
        #
        # or:
        #
        # {"file_path": "D:\\path\\file.html"}
        # ------------------------------------------------------

        if cleaned.startswith("{"):
            try:
                data = json.loads(cleaned)

            except json.JSONDecodeError as exc:
                raise ValueError(
                    "Invalid JSON document arguments."
                ) from exc

            if not isinstance(data, dict):
                raise ValueError(
                    "Document arguments must be a JSON object."
                )

            cleaned = data.get(
                "file_path",
                ""
            )

        if not isinstance(cleaned, str):
            raise TypeError(
                "Document file path must be a string."
            )

        cleaned = cleaned.strip()

        if not cleaned:
            raise ValueError(
                "Document file path cannot be empty."
            )

        return read_document(cleaned)


class DocumentInfoTool(BaseTool):
    name = "document_info"

    description = (
        "Get metadata about a supported document. "
        "Arguments may be either a plain file path or "
        "JSON containing a 'file_path' field."
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "Document path arguments must be a string."
            )

        cleaned = arguments.strip()

        if cleaned.startswith("{"):
            try:
                data = json.loads(cleaned)

            except json.JSONDecodeError as exc:
                raise ValueError(
                    "Invalid JSON document arguments."
                ) from exc

            if not isinstance(data, dict):
                raise ValueError(
                    "Document arguments must be a JSON object."
                )

            cleaned = data.get(
                "file_path",
                ""
            )

        if not isinstance(cleaned, str):
            raise TypeError(
                "Document file path must be a string."
            )

        cleaned = cleaned.strip()

        if not cleaned:
            raise ValueError(
                "Document file path cannot be empty."
            )

        return document_info(cleaned)


class SearchDocumentTool(BaseTool):
    name = "search_document"

    description = (
        "Search for text inside a supported document. "
        "Arguments must be JSON containing "
        "'file_path' and 'query'."
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "Search arguments must be a JSON string."
            )

        data = json.loads(arguments)

        if not isinstance(data, dict):
            raise ValueError(
                "Search arguments must be a JSON object."
            )

        file_path = data.get(
            "file_path",
            ""
        )

        query = data.get(
            "query",
            ""
        )

        if not isinstance(file_path, str):
            raise TypeError(
                "'file_path' must be a string."
            )

        if not isinstance(query, str):
            raise TypeError(
                "'query' must be a string."
            )

        return search_document(
            file_path=file_path,
            query=query,
        )


class DocumentSummaryTool(BaseTool):
    name = "document_summary"

    description = (
        "Generate a simple extractive summary of a "
        "supported document. Arguments must be JSON "
        "containing 'file_path' and optionally "
        "'max_words'."
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "Summary arguments must be a JSON string."
            )

        data = json.loads(arguments)

        if not isinstance(data, dict):
            raise ValueError(
                "Summary arguments must be a JSON object."
            )

        file_path = data.get(
            "file_path",
            ""
        )

        max_words = data.get(
            "max_words",
            100
        )

        if not isinstance(file_path, str):
            raise TypeError(
                "'file_path' must be a string."
            )

        if not isinstance(max_words, int):
            raise TypeError(
                "'max_words' must be an integer."
            )

        return get_document_summary(
            file_path=file_path,
            max_words=max_words,
        )


# ==========================================================
# KNOWLEDGE BASE / RAG TOOL
# ==========================================================

class SearchKnowledgeTool(BaseTool):
    name = "search_knowledge"

    description = (
        "Search the V.A.U.L.T. knowledge base using semantic retrieval. "
        "Use this tool for organization-specific, internal, or knowledge-base "
        "questions. Arguments must be JSON containing 'query' and optionally "
        "'top_k' and 'distance_threshold'. Results include the retrieved "
        "text, source document, page, and retrieval distance."
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "Knowledge search arguments must be a JSON string."
            )

        try:
            data = json.loads(arguments)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Invalid JSON knowledge search arguments."
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "Knowledge search arguments must be a JSON object."
            )

        query = data.get(
            "query",
            ""
        )

        top_k = data.get(
            "top_k",
            4
        )

        distance_threshold = data.get(
            "distance_threshold",
            1.3
        )

        if not isinstance(query, str):
            raise TypeError(
                "'query' must be a string."
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "'query' cannot be empty."
            )

        if not isinstance(top_k, int):
            raise TypeError(
                "'top_k' must be an integer."
            )

        if not isinstance(distance_threshold, (int, float)):
            raise TypeError(
                "'distance_threshold' must be a number."
            )

        if top_k < 1:
            raise ValueError(
                "'top_k' must be at least 1."
            )

        if distance_threshold <= 0:
            raise ValueError(
                "'distance_threshold' must be greater than 0."
            )

        return search_knowledge(
            query=query,
            top_k=top_k,
            distance_threshold=distance_threshold,
        )


# ==========================================================
# SYSTEM DATE/TIME TOOL
# ==========================================================

class CurrentDateTimeTool(BaseTool):
    name = "get_current_datetime"

    description = (
        "Get the current local date, time, and day of the week. "
        "Use this tool when the user asks about today's date, "
        "the current time, the current day, or similar "
        "date/time information."
    )

    def execute(self, arguments: Any) -> Any:
        """
        Return the current local date and time.

        This tool does not require any arguments.
        """

        return get_current_datetime()
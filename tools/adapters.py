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

        return file_exists(arguments)


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
        "Read a supported text-based document. "
        "Arguments should be the document file path."
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "Document path must be a string."
            )

        return read_document(arguments)


class DocumentInfoTool(BaseTool):
    name = "document_info"

    description = (
        "Get metadata about a supported text-based document. "
        "Arguments should be the document file path."
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "Document path must be a string."
            )

        return document_info(arguments)


class SearchDocumentTool(BaseTool):
    name = "search_document"

    description = (
        "Search for text inside a supported document. "
        "Arguments must be JSON containing 'file_path' "
        "and 'query'."
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "Search arguments must be a JSON string."
            )

        data = json.loads(arguments)

        return search_document(
            file_path=data["file_path"],
            query=data["query"],
        )


class DocumentSummaryTool(BaseTool):
    name = "document_summary"

    description = (
        "Generate a simple extractive summary of a supported "
        "document. Arguments must be JSON containing "
        "'file_path' and optionally 'max_words'."
    )

    def execute(self, arguments: Any) -> Any:
        if not isinstance(arguments, str):
            raise TypeError(
                "Summary arguments must be a JSON string."
            )

        data = json.loads(arguments)

        return get_document_summary(
            file_path=data["file_path"],
            max_words=data.get("max_words", 100),
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
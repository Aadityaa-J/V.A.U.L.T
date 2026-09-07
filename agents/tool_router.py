from typing import Any, Dict, Optional
import json
import re


class ToolRouter:
    """
    Deterministic tool intent router for V.A.U.L.T.

    Detects obvious user requests and converts them into
    direct tool calls.

    Supported tools:

    - calculate
    - get_current_datetime
    - list_files
    - list_directory
    - file_exists
    - create_directory
    - copy_file
    - move_file
    - read_document
    - document_info
    - search_document
    - document_summary
    - run_python
    """

    def route(
        self,
        task: str,
        available_tools: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Determine whether a task should directly execute
        a tool.

        Returns:

            {
                "name": "tool_name",
                "arguments": "tool arguments"
            }

        Or:

            None

        when the LLM should handle the task normally.
        """

        if not isinstance(task, str):
            raise TypeError(
                "Task must be a string."
            )

        if not isinstance(
            available_tools,
            dict,
        ):
            raise TypeError(
                "Available tools must be a dictionary."
            )

        cleaned_task = task.strip()

        if not cleaned_task:
            return None

        task_lower = cleaned_task.lower()

        # ======================================================
        # CALCULATOR
        # ======================================================

        calculation = (
            self._detect_calculation(
                cleaned_task
            )
        )

        if (
            calculation is not None
            and "calculate" in available_tools
        ):

            return {
                "name": "calculate",
                "arguments": calculation,
            }

        # ======================================================
        # CURRENT DATE / TIME
        # ======================================================

        datetime_result = (
            self._detect_datetime(
                task_lower
            )
        )

        if (
            datetime_result
            and "get_current_datetime"
            in available_tools
        ):

            return {
                "name": (
                    "get_current_datetime"
                ),
                "arguments": "",
            }

        # ======================================================
        # LIST FILES
        # ======================================================

        directory = (
            self._detect_list_files(
                cleaned_task,
                task_lower,
            )
        )

        if (
            directory is not None
            and "list_files"
            in available_tools
        ):

            return {
                "name": "list_files",
                "arguments": directory,
            }

        # ======================================================
        # LIST DIRECTORY
        # ======================================================

        directory = (
            self._detect_list_directory(
                cleaned_task,
                task_lower,
            )
        )

        if (
            directory is not None
            and "list_directory"
            in available_tools
        ):

            return {
                "name": "list_directory",
                "arguments": directory,
            }

        # ======================================================
        # FILE EXISTS
        # ======================================================

        file_path = (
            self._detect_file_exists(
                cleaned_task,
                task_lower,
            )
        )

        if (
            file_path is not None
            and "file_exists"
            in available_tools
        ):

            return {
                "name": "file_exists",
                "arguments": file_path,
            }

        # ======================================================
        # CREATE DIRECTORY
        # ======================================================

        directory = (
            self._detect_create_directory(
                cleaned_task,
                task_lower,
            )
        )

        if (
            directory is not None
            and "create_directory"
            in available_tools
        ):

            return {
                "name": "create_directory",
                "arguments": directory,
            }

        # ======================================================
        # READ DOCUMENT
        # ======================================================

        file_path = (
            self._detect_read_document(
                cleaned_task,
                task_lower,
            )
        )

        if (
            file_path is not None
            and "read_document"
            in available_tools
        ):

            return {
                "name": "read_document",
                "arguments": file_path,
            }

        # ======================================================
        # DOCUMENT INFO
        # ======================================================

        file_path = (
            self._detect_document_info(
                cleaned_task,
                task_lower,
            )
        )

        if (
            file_path is not None
            and "document_info"
            in available_tools
        ):

            return {
                "name": "document_info",
                "arguments": file_path,
            }

        # ======================================================
        # DOCUMENT SUMMARY
        # ======================================================

        summary_data = (
            self._detect_document_summary(
                cleaned_task,
                task_lower,
            )
        )

        if (
            summary_data is not None
            and "document_summary"
            in available_tools
        ):

            return {
                "name": "document_summary",
                "arguments": json.dumps(
                    summary_data
                ),
            }

        # ======================================================
        # SEARCH DOCUMENT
        # ======================================================

        search_data = (
            self._detect_document_search(
                cleaned_task,
                task_lower,
            )
        )

        if (
            search_data is not None
            and "search_document"
            in available_tools
        ):

            return {
                "name": "search_document",
                "arguments": json.dumps(
                    search_data
                ),
            }

        # ======================================================
        # NO DIRECT TOOL MATCH
        # ======================================================

        return None

    # ==========================================================
    # CALCULATION DETECTION
    # ==========================================================

    def _detect_calculation(
        self,
        task: str,
    ) -> Optional[str]:

        expression = task.strip()

        prefixes = [
            "calculate",
            "compute",
            "evaluate",
            "solve",
            "what is",
            "find",
        ]

        task_lower = expression.lower()

        for prefix in prefixes:

            if task_lower.startswith(prefix):

                expression = (
                    expression[
                        len(prefix):
                    ]
                    .strip()
                )

                break

        expression = (
            expression
            .rstrip("?")
            .rstrip(".")
            .strip()
        )

        if not expression:
            return None

        # Only mathematical characters allowed.

        pattern = (
            r"^[0-9\s\+\-\*\/\%\.\(\)]+$"
        )

        if not re.fullmatch(
            pattern,
            expression,
        ):
            return None

        # Require at least one operator.

        operators = [
            "+",
            "-",
            "*",
            "/",
            "%",
        ]

        if not any(
            operator in expression
            for operator in operators
        ):
            return None

        if len(expression) > 200:
            return None

        return expression

    # ==========================================================
    # DATE / TIME DETECTION
    # ==========================================================

    def _detect_datetime(
        self,
        task_lower: str,
    ) -> bool:

        keywords = [
            "what time is it",
            "current time",
            "time now",
            "what is the time",
            "what day is it",
            "current day",
            "today's date",
            "todays date",
            "what is today's date",
            "what is the date",
            "current date",
            "date today",
        ]

        return any(
            keyword in task_lower
            for keyword in keywords
        )

    # ==========================================================
    # LIST FILES DETECTION
    # ==========================================================

    def _detect_list_files(
        self,
        task: str,
        task_lower: str,
    ) -> Optional[str]:

        patterns = [
            "list files",
            "show files",
            "what files",
            "files in",
        ]

        if not any(
            pattern in task_lower
            for pattern in patterns
        ):
            return None

        directory = self._extract_path(
            task
        )

        return directory or "."

    # ==========================================================
    # LIST DIRECTORY DETECTION
    # ==========================================================

    def _detect_list_directory(
        self,
        task: str,
        task_lower: str,
    ) -> Optional[str]:

        patterns = [
            "list directory",
            "show directory",
            "show folders",
            "list folders",
            "directory contents",
        ]

        if not any(
            pattern in task_lower
            for pattern in patterns
        ):
            return None

        directory = self._extract_path(
            task
        )

        return directory or "."

    # ==========================================================
    # FILE EXISTS DETECTION
    # ==========================================================

    def _detect_file_exists(
        self,
        task: str,
        task_lower: str,
    ) -> Optional[str]:

        patterns = [
            "does file exist",
            "does the file exist",
            "file exists",
            "check if",
            "check whether",
        ]

        if not any(
            pattern in task_lower
            for pattern in patterns
        ):
            return None

        return self._extract_path(
            task
        )

    # ==========================================================
    # CREATE DIRECTORY DETECTION
    # ==========================================================

    def _detect_create_directory(
        self,
        task: str,
        task_lower: str,
    ) -> Optional[str]:

        patterns = [
            "create directory",
            "create folder",
            "make directory",
            "make folder",
            "new directory",
            "new folder",
        ]

        if not any(
            pattern in task_lower
            for pattern in patterns
        ):
            return None

        return self._extract_path(
            task
        )

    # ==========================================================
    # READ DOCUMENT DETECTION
    # ==========================================================

    def _detect_read_document(
        self,
        task: str,
        task_lower: str,
    ) -> Optional[str]:

        patterns = [
            "read document",
            "read file",
            "open document",
            "open file",
            "show document",
            "show file",
        ]

        if not any(
            pattern in task_lower
            for pattern in patterns
        ):
            return None

        return self._extract_path(
            task
        )

    # ==========================================================
    # DOCUMENT INFO DETECTION
    # ==========================================================

    def _detect_document_info(
        self,
        task: str,
        task_lower: str,
    ) -> Optional[str]:

        patterns = [
            "document info",
            "file info",
            "document information",
            "file information",
            "information about file",
        ]

        if not any(
            pattern in task_lower
            for pattern in patterns
        ):
            return None

        return self._extract_path(
            task
        )

    # ==========================================================
    # DOCUMENT SUMMARY DETECTION
    # ==========================================================

    def _detect_document_summary(
        self,
        task: str,
        task_lower: str,
    ) -> Optional[Dict[str, Any]]:

        patterns = [
            "summarize document",
            "summarise document",
            "summarize file",
            "summarise file",
            "summary of",
        ]

        if not any(
            pattern in task_lower
            for pattern in patterns
        ):
            return None

        file_path = self._extract_path(
            task
        )

        if not file_path:
            return None

        return {
            "file_path": file_path,
            "max_words": 100,
        }

    # ==========================================================
    # DOCUMENT SEARCH DETECTION
    # ==========================================================

    def _detect_document_search(
        self,
        task: str,
        task_lower: str,
    ) -> Optional[Dict[str, str]]:

        # Example:
        #
        # Search "pressure" in report.txt

        match = re.search(
            r'search\s+["\'](.+?)["\']'
            r'\s+(?:in|inside)\s+(.+)',
            task,
            re.IGNORECASE,
        )

        if not match:
            return None

        query = match.group(1).strip()

        file_path = (
            match.group(2)
            .strip()
            .rstrip("?")
            .rstrip(".")
        )

        if not query or not file_path:
            return None

        return {
            "file_path": file_path,
            "query": query,
        }

    # ==========================================================
    # PATH EXTRACTION
    # ==========================================================

    def _extract_path(
        self,
        task: str,
    ) -> Optional[str]:
        """
        Extract a possible path from a user request.

        Supports:

            C:\\folder\\file.txt
            ./file.txt
            ../file.txt
            folder/file.txt
            "file.txt"
        """

        # ------------------------------------------------------
        # QUOTED PATH
        # ------------------------------------------------------

        quoted_match = re.search(
            r'["\']([^"\']+)["\']',
            task,
        )

        if quoted_match:

            return (
                quoted_match
                .group(1)
                .strip()
            )

        # ------------------------------------------------------
        # WINDOWS PATH
        # ------------------------------------------------------

        windows_match = re.search(
            r'[A-Za-z]:\\[^\s]+',
            task,
        )

        if windows_match:

            return (
                windows_match
                .group(0)
                .strip()
            )

        # ------------------------------------------------------
        # RELATIVE PATH
        # ------------------------------------------------------

        relative_match = re.search(
            r'(?:\.\.?[\\/][^\s]+)',
            task,
        )

        if relative_match:

            return (
                relative_match
                .group(0)
                .strip()
            )

        # ------------------------------------------------------
        # FILE NAME
        # ------------------------------------------------------

        file_match = re.search(
            r'\b[\w\-. ]+\.'
            r'(?:txt|md|json|csv|pdf|docx)\b',
            task,
            re.IGNORECASE,
        )

        if file_match:

            return (
                file_match
                .group(0)
                .strip()
            )

        return None
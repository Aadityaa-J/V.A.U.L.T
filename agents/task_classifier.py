"""
Fast Task Classifier for V.A.U.L.T.

Uses deterministic rules for common tasks.

This avoids unnecessary Ollama calls and makes
agent selection significantly faster.
"""

import re

from models.llm import generate
from models.router import select_model


class TaskClassifier:

    def __init__(self):
        self.task_type = "classification"

    # ==========================================================
    # MAIN CLASSIFICATION
    # ==========================================================

    def classify(self, task: str) -> str:
        """
        Classify a user task into one of:

        - document
        - coding
        - engineering
        - general

        Classification order:

        1. Fast deterministic rules.
        2. Mathematical expression detection.
        3. LLM fallback for ambiguous requests.
        """

        if not isinstance(task, str):
            raise TypeError(
                "Task must be a string."
            )

        task = task.strip()

        if not task:
            raise ValueError(
                "Task cannot be empty."
            )

        task_lower = task.lower()

        # --------------------------------------------------
        # DOCUMENT
        # --------------------------------------------------

        if self._is_document_task(
            task_lower
        ):
            return "document"

        # --------------------------------------------------
        # CODING
        # --------------------------------------------------

        if self._is_coding_task(
            task_lower
        ):
            return "coding"

        # --------------------------------------------------
        # ENGINEERING
        # --------------------------------------------------

        if self._is_engineering_task(
            task_lower
        ):
            return "engineering"

        # --------------------------------------------------
        # PURE MATHEMATICAL EXPRESSION
        # --------------------------------------------------

        if self._is_math_expression(
            task
        ):
            return "engineering"

        # --------------------------------------------------
        # GENERAL
        #
        # Most normal conversation should NOT require
        # an expensive LLM classification call.
        # --------------------------------------------------

        if self._is_general_task(
            task_lower
        ):
            return "general"

        # --------------------------------------------------
        # LLM FALLBACK
        #
        # Only ambiguous requests reach this point.
        # --------------------------------------------------

        return self._llm_classify(
            task
        )

    # ==========================================================
    # DOCUMENT DETECTION
    # ==========================================================

    def _is_document_task(
        self,
        task: str
    ) -> bool:

        keywords = [

            "read this document",
            "read document",

            "read this file",
            "read file",

            "summarize document",
            "summarize this document",

            "summarize file",
            "summarize this file",

            "search document",
            "search file",

            "analyze document",
            "analyse document",

            "document information",
            "document info",

            "extract from document",
            "extract from file",

            "search inside",

            ".txt",
            ".md",
            ".json",
            ".csv",

            "pdf",

        ]

        return any(
            keyword in task
            for keyword in keywords
        )

    # ==========================================================
    # CODING DETECTION
    # ==========================================================

    def _is_coding_task(
        self,
        task: str
    ) -> bool:

        keywords = [

            "python",
            "javascript",
            "typescript",

            "write code",
            "write a program",

            "write a function",

            "create a function",

            "debug code",
            "debug this",

            "fix this code",

            "bug in",

            "programming",

            "software development",

            "algorithm",

            "class ",

            "function ",

            "script",

            "api",

            "database code",

            "html",

            "css",

            "sql",

            "run python",

            "execute python",

        ]

        return any(
            keyword in task
            for keyword in keywords
        )

    # ==========================================================
    # ENGINEERING DETECTION
    # ==========================================================

    def _is_engineering_task(
        self,
        task: str
    ) -> bool:

        keywords = [

            # Calculations
            "calculate",
            "calculation",

            "solve",

            "multiply",
            "multiplied",

            "divide",
            "division",

            "addition",

            "subtract",
            "subtraction",

            # Engineering
            "engineering",

            "force",

            "pressure",

            "velocity",

            "speed calculation",

            "acceleration",

            "mass",

            "weight",

            "density",

            "volume",

            "temperature",

            "heat",

            "energy",

            "power",

            "torque",

            "stress",

            "strain",

            # Electrical
            "voltage",

            "current",

            "resistance",

            "ohm",

            "watt",

            "ampere",

            # Mechanical
            "mechanical",

            "load",

            "bearing",

            "shaft",

            "gear",

            # Units
            "kg",

            "kilogram",

            "meters",

            "meter",

            "newton",

            "pascal",

        ]

        return any(
            keyword in task
            for keyword in keywords
        )

    # ==========================================================
    # MATHEMATICAL EXPRESSION DETECTION
    # ==========================================================

    def _is_math_expression(
        self,
        task: str
    ) -> bool:
        """
        Detect expressions such as:

            25 * 48
            100 / 4
            (10 + 5) * 2
            2 ** 8
            10 + 20
        """

        expression = task.strip()

        # Remove spaces.
        compact = re.sub(
            r"\s+",
            "",
            expression
        )

        if not compact:
            return False

        # Must contain at least one mathematical operator.
        if not re.search(
            r"[+\-*/%]",
            compact
        ):
            return False

        # Only allow numeric mathematical characters.
        valid_pattern = (
            r"^[0-9+\-*/%().]+$"
        )

        if re.fullmatch(
            valid_pattern,
            compact
        ):

            return True

        return False

    # ==========================================================
    # GENERAL CONVERSATION DETECTION
    # ==========================================================

    def _is_general_task(
        self,
        task: str
    ) -> bool:

        general_keywords = [

            "hello",

            "hi",

            "hey",

            "how are you",

            "what is your name",

            "who are you",

            "good morning",

            "good afternoon",

            "good evening",

            "thank you",

            "thanks",

            "bye",

            "goodbye",

            "tell me about",

            "what do you think",

        ]

        if any(
            keyword in task
            for keyword in general_keywords
        ):
            return True

        # Short questions without strong technical signals
        # are usually general.

        words = task.split()

        if len(words) <= 5:

            return True

        return False

    # ==========================================================
    # LLM FALLBACK
    # ==========================================================

    def _llm_classify(
        self,
        task: str
    ) -> str:
        """
        Use the fast model only when deterministic
        classification is uncertain.
        """

        model = select_model(
            self.task_type
        )

        prompt = f"""
You are the task classifier for V.A.U.L.T.

Classify the user's task into exactly ONE category:

document
coding
engineering
general

Definitions:

document:
Reading, searching, analyzing, summarizing,
extracting, or interpreting a document or file.

coding:
Writing, debugging, modifying, executing,
or explaining computer code.

engineering:
Technical calculations, engineering problems,
physical quantities, formulas, measurements,
or technical analysis.

general:
Normal conversation or anything that does not
clearly belong to the other categories.

If uncertain, choose general.

User task:

{task}

Respond with ONLY one category name.
"""

        try:

            response = generate(
                prompt=prompt,
                model=model,
                use_router=False,
            )

            result = (
                response
                .strip()
                .lower()
            )

        except Exception:

            # Safe fallback.
            return "general"

        valid_categories = {

            "document",

            "coding",

            "engineering",

            "general",

        }

        if result in valid_categories:

            return result

        return "general"


# ==========================================================
# TEST MODE
# ==========================================================

if __name__ == "__main__":

    classifier = TaskClassifier()

    test_tasks = [

        "Calculate 25 * 48",

        "25 * 48",

        "100 / 4",

        "(10 + 5) * 2",

        "Write a Python function",

        "Debug this code",

        "Read this document",

        "Summarize this file",

        "Hello, how are you?",

        "What is the capital of France?",

    ]

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FAST TASK CLASSIFIER TEST"
    )

    print("=" * 60)

    for task in test_tasks:

        result = classifier.classify(
            task
        )

        print()

        print(
            f"Task: {task}"
        )

        print(
            f"Category: {result}"
        )

    print()

    print("=" * 60)

    print(
        "TEST COMPLETE"
    )

    print("=" * 60)
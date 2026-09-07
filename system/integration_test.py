"""
V.A.U.L.T. Full System Integration Test

Run with:

    python -m system.integration_test
"""

import traceback

from agents.task_classifier import TaskClassifier
from agents.orchestrator import Orchestrator
from models.router import route, select_model
from tools.calculations import calculate


# ==========================================================
# TEST RESULT TRACKER
# ==========================================================

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def success(self, test_name: str):
        self.passed += 1
        print(f"[PASS] {test_name}")

    def failure(
        self,
        test_name: str,
        error: Exception | str
    ):
        self.failed += 1
        print(f"[FAIL] {test_name}")
        print(f"       Error: {error}")

    def summary(self):
        total = self.passed + self.failed

        print("\n" + "=" * 60)
        print("V.A.U.L.T. INTEGRATION TEST SUMMARY")
        print("=" * 60)

        print(f"Total Tests: {total}")
        print(f"Passed:      {self.passed}")
        print(f"Failed:      {self.failed}")

        print("=" * 60)

        if self.failed == 0:
            print(
                "V.A.U.L.T. INTEGRATION STATUS: "
                "ALL TESTS PASSED"
            )
        else:
            print(
                "V.A.U.L.T. INTEGRATION STATUS: "
                "SOME TESTS FAILED"
            )

        print("=" * 60)


# ==========================================================
# TASK CLASSIFIER TESTS
# ==========================================================

def test_task_classifier(
    results: TestResults
):
    print("\n" + "=" * 60)
    print("TASK CLASSIFIER TESTS")
    print("=" * 60)

    classifier = TaskClassifier()

    tests = [
        (
            "Calculate 25 * 48",
            "engineering",
        ),
        (
            "25 * 48",
            "engineering",
        ),
        (
            "Write a Python function",
            "coding",
        ),
        (
            "Debug this Python code",
            "coding",
        ),
        (
            "Read this document",
            "document",
        ),
        (
            "Summarize this file",
            "document",
        ),
        (
            "Hello, how are you?",
            "general",
        ),
    ]

    for task, expected in tests:

        test_name = (
            f"Classify: '{task}'"
        )

        try:

            result = classifier.classify(
                task
            )

            if result == expected:

                results.success(
                    test_name
                )

            else:

                results.failure(
                    test_name,
                    (
                        f"Expected '{expected}', "
                        f"got '{result}'"
                    )
                )

        except Exception as exc:

            results.failure(
                test_name,
                exc
            )


# ==========================================================
# MODEL ROUTER TESTS
# ==========================================================

def test_model_router(
    results: TestResults
):
    print("\n" + "=" * 60)
    print("MODEL ROUTER TESTS")
    print("=" * 60)

    tests = [
        (
            "simple",
        ),
        (
            "complex",
        ),
        (
            "visual",
        ),
    ]

    for task_type_tuple in tests:

        task_type = task_type_tuple[0]

        test_name = (
            f"Select model: '{task_type}'"
        )

        try:

            model = select_model(
                task_type
            )

            if isinstance(
                model,
                str
            ) and model.strip():

                results.success(
                    test_name
                )

            else:

                results.failure(
                    test_name,
                    "Invalid model returned."
                )

        except Exception as exc:

            results.failure(
                test_name,
                exc
            )

    # ----------------------------------------------
    # SMART ROUTING TEST
    # ----------------------------------------------

    routing_tests = [
        "Hello, how are you?",
        "Write a Python function",
        "Calculate 25 * 48",
    ]

    for prompt in routing_tests:

        test_name = (
            f"Route prompt: '{prompt}'"
        )

        try:

            model = route(
                prompt
            )

            if isinstance(
                model,
                str
            ) and model.strip():

                results.success(
                    test_name
                )

            else:

                results.failure(
                    test_name,
                    "Router returned invalid model."
                )

        except Exception as exc:

            results.failure(
                test_name,
                exc
            )


# ==========================================================
# CALCULATOR TESTS
# ==========================================================

def test_calculator(
    results: TestResults
):
    print("\n" + "=" * 60)
    print("CALCULATOR TESTS")
    print("=" * 60)

    tests = [
        (
            "25 * 48",
            1200,
        ),
        (
            "10 + 5",
            15,
        ),
        (
            "100 / 4",
            25,
        ),
        (
            "(10 + 5) * 2",
            30,
        ),
        (
            "2 ** 8",
            256,
        ),
    ]

    for expression, expected in tests:

        test_name = (
            f"Calculate: {expression}"
        )

        try:

            result = calculate(
                expression
            )

            if result == expected:

                results.success(
                    test_name
                )

            else:

                results.failure(
                    test_name,
                    (
                        f"Expected {expected}, "
                        f"got {result}"
                    )
                )

        except Exception as exc:

            results.failure(
                test_name,
                exc
            )


# ==========================================================
# ORCHESTRATOR TEST
# ==========================================================

def test_orchestrator(
    results: TestResults
):
    print("\n" + "=" * 60)
    print("FULL ORCHESTRATOR TEST")
    print("=" * 60)

    try:

        print(
            "\nInitializing Orchestrator..."
        )

        orchestrator = Orchestrator()

        results.success(
            "Orchestrator initialization"
        )

    except Exception as exc:

        results.failure(
            "Orchestrator initialization",
            exc
        )

        return

    # ----------------------------------------------
    # GENERAL TASK
    # ----------------------------------------------

    try:

        print(
            "\nRunning general agent test..."
        )

        response = orchestrator.run(
            "Hello V.A.U.L.T."
        )

        if (
            isinstance(response, str)
            and response.strip()
        ):

            results.success(
                "General agent pipeline"
            )

        else:

            results.failure(
                "General agent pipeline",
                "Empty response."
            )

    except Exception as exc:

        results.failure(
            "General agent pipeline",
            exc
        )

    # ----------------------------------------------
    # ENGINEERING TASK
    # ----------------------------------------------

    try:

        print(
            "\nRunning engineering agent test..."
        )

        response = orchestrator.run(
            "Calculate 25 * 48"
        )

        if (
            isinstance(response, str)
            and response.strip()
        ):

            results.success(
                "Engineering agent pipeline"
            )

            print(
                f"\nResponse: {response}"
            )

        else:

            results.failure(
                "Engineering agent pipeline",
                "Empty response."
            )

    except Exception as exc:

        results.failure(
            "Engineering agent pipeline",
            exc
        )

    # ----------------------------------------------
    # CODING TASK
    # ----------------------------------------------

    try:

        print(
            "\nRunning coding agent test..."
        )

        response = orchestrator.run(
            "Write a simple Python function "
            "that adds two numbers."
        )

        if (
            isinstance(response, str)
            and response.strip()
        ):

            results.success(
                "Coding agent pipeline"
            )

        else:

            results.failure(
                "Coding agent pipeline",
                "Empty response."
            )

    except Exception as exc:

        results.failure(
            "Coding agent pipeline",
            exc
        )

    # ----------------------------------------------
    # SESSION TEST
    # ----------------------------------------------

    try:

        history = (
            orchestrator.get_session_history()
        )

        if (
            isinstance(history, list)
            and len(history) > 0
        ):

            results.success(
                "Session memory storage"
            )

        else:

            results.failure(
                "Session memory storage",
                "Session history is empty."
            )

    except Exception as exc:

        results.failure(
            "Session memory storage",
            exc
        )

    # ----------------------------------------------
    # PERSISTENT MEMORY TEST
    # ----------------------------------------------

    try:

        memory = orchestrator.get_memory()

        if isinstance(memory, list):

            results.success(
                "Persistent memory system"
            )

        else:

            results.failure(
                "Persistent memory system",
                "Memory returned invalid format."
            )

    except Exception as exc:

        results.failure(
            "Persistent memory system",
            exc
        )


# ==========================================================
# MAIN
# ==========================================================

def main():

    print("\n" + "=" * 60)
    print("V.A.U.L.T. FULL SYSTEM INTEGRATION TEST")
    print("=" * 60)

    print(
        "\nTesting the complete V.A.U.L.T. system..."
    )

    results = TestResults()

    # ----------------------------------------------
    # RUN TESTS
    # ----------------------------------------------

    test_task_classifier(
        results
    )

    test_model_router(
        results
    )

    test_calculator(
        results
    )

    test_orchestrator(
        results
    )

    # ----------------------------------------------
    # FINAL SUMMARY
    # ----------------------------------------------

    results.summary()

    # ----------------------------------------------
    # EXIT STATUS
    # ----------------------------------------------

    if results.failed > 0:

        raise SystemExit(1)

    raise SystemExit(0)


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\n\nIntegration test interrupted."
        )

        raise SystemExit(130)

    except Exception:

        print(
            "\nUnexpected integration "
            "test failure:\n"
        )

        traceback.print_exc()

        raise SystemExit(1)
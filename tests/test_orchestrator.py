from agents.orchestrator import Orchestrator


def main():
    print("=" * 60)
    print("ORCHESTRATOR AUTOMATIC ROUTING TEST")
    print("=" * 60)

    orchestrator = Orchestrator()

    print(
        "\nCalculator registered:",
        orchestrator.tool_registry.has("calculate")
    )

    assert orchestrator.tool_registry.has(
        "calculate"
    )

    print("\n" + "-" * 60)
    print("TEST 1: DOCUMENT")
    print("-" * 60)

    document_task = (
        "Summarize the findings in this inspection report."
    )

    document_result = orchestrator.run(
        document_task
    )

    print("Task:", document_task)
    print("\nResult:")
    print(document_result)

    print("\n" + "-" * 60)
    print("TEST 2: CODING")
    print("-" * 60)

    coding_task = (
        "Write a Python function that calculates the "
        "factorial of a number."
    )

    coding_result = orchestrator.run(
        coding_task
    )

    print("Task:", coding_task)
    print("\nResult:")
    print(coding_result)

    print("\n" + "-" * 60)
    print("TEST 3: ENGINEERING")
    print("-" * 60)

    engineering_task = (
        "Calculate the pump efficiency from the given "
        "measurements."
    )

    engineering_result = orchestrator.run(
        engineering_task
    )

    print("Task:", engineering_task)
    print("\nResult:")
    print(engineering_result)

    print("\n" + "=" * 60)
    print("AUTOMATIC ROUTING TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
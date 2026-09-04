from agents.orchestrator import Orchestrator


def main():
    print("=" * 60)
    print("REAL LLM TOOL SELECTION TEST")
    print("=" * 60)

    orchestrator = Orchestrator()

    task = """
Calculate 125 multiplied by 8.

Use the available calculator tool to perform the calculation.
Do not calculate the result yourself.
"""

    print("\nTASK:")
    print(task)

    print("\nRunning real agent...\n")

    result = orchestrator.run(task)

    print("=" * 60)
    print("FINAL RESULT")
    print("=" * 60)

    print(result)

    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
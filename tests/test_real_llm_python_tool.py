from agents.orchestrator import Orchestrator


def main():
    print("=" * 60)
    print("REAL LLM PYTHON TOOL SELECTION TEST")
    print("=" * 60)

    orchestrator = Orchestrator()

    task = """
Use the available Python execution tool to run Python code.

Calculate the sum of the numbers from 1 to 10.

Do not calculate the answer manually.
Use the Python tool and then report the result.
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
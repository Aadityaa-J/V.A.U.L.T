from agents.orchestrator import Orchestrator


def main():

    print()
    print("=" * 60)
    print("V.A.U.L.T. ORCHESTRATOR TEST")
    print("=" * 60)

    print()
    print("Initializing Orchestrator...")

    orchestrator = Orchestrator()

    print("Orchestrator initialized successfully.")

    print()
    print("-" * 60)
    print("TEST 1: GENERAL CONVERSATION")
    print("-" * 60)

    task = "Hello, how are you?"

    print()
    print(f"USER: {task}")

    try:

        result = orchestrator.run(task)

        print()
        print("V.A.U.L.T.:")
        print(result)

    except Exception as exc:

        print()
        print("ERROR:")
        print(type(exc).__name__)
        print(exc)

    print()
    print("=" * 60)
    print("ORCHESTRATOR TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()

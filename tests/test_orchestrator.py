@'
from agents.orchestrator import Orchestrator


def run_test(orchestrator, task):

    print()
    print("=" * 60)
    print(f"USER: {task}")
    print("=" * 60)

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


def main():

    print()
    print("=" * 60)
    print("V.A.U.L.T. ORCHESTRATOR MULTI-TEST")
    print("=" * 60)

    print()
    print("Initializing Orchestrator...")

    orchestrator = Orchestrator()

    print("Orchestrator initialized successfully.")

    # ---------------------------------------------
    # TEST 1
    # ---------------------------------------------

    run_test(
        orchestrator,
        "Hello, how are you?"
    )

    # ---------------------------------------------
    # TEST 2
    # Tests conversation memory
    # ---------------------------------------------

    run_test(
        orchestrator,
        "What did I just ask you?"
    )

    # ---------------------------------------------
    # TEST 3
    # Tests general knowledge routing
    # ---------------------------------------------

    run_test(
        orchestrator,
        "Explain what artificial intelligence is in simple words."
    )

    # ---------------------------------------------
    # SESSION HISTORY
    # ---------------------------------------------

    print()
    print("=" * 60)
    print("SESSION HISTORY")
    print("=" * 60)

    history = orchestrator.get_session_history()

    for message in history:

        print()
        print(
            f"{message['role'].upper()}:"
        )

        print(
            message['content']
        )

    print()
    print("=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
'@ | Set-Content test_orchestrator.py
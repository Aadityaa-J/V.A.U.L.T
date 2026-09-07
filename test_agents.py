from agents.orchestrator import Orchestrator


def main():

    print()
    print("=" * 60)
    print("V.A.U.L.T. AGENT ROUTING TEST")
    print("=" * 60)

    vault = Orchestrator()

    tests = [

        (
            "GENERAL",
            "Hello! Tell me what you can do."
        ),

        (
            "CODING",
            "Write a simple Python function that adds two numbers."
        ),

        (
            "ENGINEERING",
            "Calculate the force when a 10 kg object accelerates at 5 m/s^2."
        ),

    ]

    for expected_agent, task in tests:

        print()
        print("=" * 60)
        print(f"EXPECTED TASK TYPE: {expected_agent}")
        print("=" * 60)

        print()
        print(f"USER: {task}")

        try:

            task_type = vault.classifier.classify(task)

            print()
            print(f"CLASSIFIED AS: {task_type.upper()}")

            print()

            result = vault.run(task)

            print("V.A.U.L.T.:")
            print(result)

        except Exception as exc:

            print()
            print("ERROR:")
            print(type(exc).__name__)
            print(exc)

    print()
    print("=" * 60)
    print("AGENT ROUTING TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()

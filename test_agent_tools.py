from agents.orchestrator import Orchestrator


def main():

    print()
    print("=" * 60)
    print("V.A.U.L.T. AGENT TOOL PIPELINE TEST")
    print("=" * 60)

    vault = Orchestrator()

    tests = [
        "Calculate 123 * 456",
        "Write a Python function that calculates factorial of 5.",
    ]

    for number, task in enumerate(tests, start=1):

        print()
        print("=" * 60)
        print(f"TEST {number}")
        print("=" * 60)

        print()
        print("USER:")
        print(task)

        print()
        print("V.A.U.L.T.:")

        try:
            result = vault.run(task)
            print(result)

        except Exception as error:
            print()
            print("ERROR:")
            print(type(error).__name__)
            print(error)

    print()
    print("=" * 60)
    print("AGENT TOOL PIPELINE TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
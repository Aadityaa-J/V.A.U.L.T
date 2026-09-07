from agents.orchestrator import Orchestrator


def main():

    print()
    print("=" * 60)
    print("V.A.U.L.T. FULL SYSTEM TEST")
    print("=" * 60)

    vault = Orchestrator()

    tests = [

        "Hello! What can you do?",

        "Calculate 25 * 48",

        "Write a Python function that checks if a number is even.",

        "Calculate the force of a 20 kg object accelerating at 3 m/s^2.",

    ]

    for index, task in enumerate(tests, start=1):

        print()
        print("=" * 60)
        print(f"TEST {index}")
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
    print("FULL SYSTEM TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
from agents.orchestrator import Orchestrator


def print_banner():

    print()
    print("=" * 60)
    print("V.A.U.L.T.")
    print("Versatile Autonomous Unified Logic Terminal")
    print("=" * 60)

    print()
    print("Local Sovereign AI System")
    print()

    print("Commands:")
    print("  exit       - Close V.A.U.L.T.")
    print("  quit       - Close V.A.U.L.T.")
    print("  clear      - Clear conversation memory")
    print("  memory     - Show persistent memory")
    print("  clearall   - Clear all memory")

    print()
    print("=" * 60)
    print()


def main():

    print_banner()

    print("Initializing V.A.U.L.T...")

    try:

        vault = Orchestrator()

    except Exception as error:

        print()
        print("FAILED TO INITIALIZE V.A.U.L.T.")
        print()
        print(type(error).__name__)
        print(error)

        return

    print()
    print("V.A.U.L.T. ONLINE")
    print()

    while True:

        try:

            user_input = input(
                "YOU > "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError,
        ):

            print()
            print()
            print("V.A.U.L.T. shutting down.")

            break

        # -----------------------------------------
        # EMPTY INPUT
        # -----------------------------------------

        if not user_input:

            continue

        command = user_input.lower()

        # -----------------------------------------
        # EXIT
        # -----------------------------------------

        if command in {

            "exit",
            "quit",

        }:

            print()
            print("V.A.U.L.T. shutting down.")

            break

        # -----------------------------------------
        # CLEAR SESSION
        # -----------------------------------------

        if command == "clear":

            vault.clear_session()

            print()
            print(
                "Conversation memory cleared."
            )
            print()

            continue

        # -----------------------------------------
        # SHOW MEMORY
        # -----------------------------------------

        if command == "memory":

            memory = vault.get_memory()

            print()

            if not memory:

                print(
                    "No persistent memory stored."
                )

            else:

                print(
                    "PERSISTENT MEMORY:"
                )

                print()

                for key, value in memory.items():

                    print(
                        f"{key}: {value}"
                    )

            print()

            continue

        # -----------------------------------------
        # CLEAR ALL MEMORY
        # -----------------------------------------

        if command == "clearall":

            vault.clear_all_memory()

            print()
            print(
                "All memory cleared."
            )
            print()

            continue

        # -----------------------------------------
        # PROCESS TASK
        # -----------------------------------------

        print()

        print(
            "V.A.U.L.T. thinking..."
        )

        print()

        try:

            result = vault.run(
                user_input
            )

            print(
                "V.A.U.L.T. >"
            )

            print(
                result
            )

        except Exception as error:

            print(
                "V.A.U.L.T. ERROR:"
            )

            print(
                type(error).__name__
            )

            print(
                error
            )

        print()


if __name__ == "__main__":

    main()
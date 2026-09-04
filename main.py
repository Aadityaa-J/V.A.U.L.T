from agents.orchestrator import Orchestrator


def print_banner() -> None:
    print("=" * 60)
    print("V.A.U.L.T. - Sovereign AI System")
    print("=" * 60)
    print("Type 'help' to see available commands.")
    print()


def print_help() -> None:
    print()
    print("Available commands:")
    print("  help                  - Show available commands")
    print("  history               - Show conversation history")
    print("  clear                 - Clear conversation history")
    print("  memory                - Show long-term memory")
    print("  forget <key>          - Forget one memory item")
    print("  clear memory          - Clear all long-term memory")
    print("  exit                  - Exit V.A.U.L.T.")
    print()


def print_memory(
    orchestrator: Orchestrator
) -> None:
    """
    Display all long-term memory.
    """

    memory = orchestrator.get_memory()

    print()

    if not memory:
        print("V.A.U.L.T. has no stored long-term memory.")

    else:
        print("V.A.U.L.T. Long-Term Memory:")

        for key, value in memory.items():
            readable_key = (
                key.replace("_", " ")
                .capitalize()
            )

            print(
                f"  {readable_key}: {value}"
            )

    print()


def forget_memory(
    orchestrator: Orchestrator,
    key: str
) -> None:
    """
    Remove one memory item.
    """

    key = key.strip()

    if not key:
        print(
            "\nUsage: forget <memory_key>\n"
        )

        return

    memory = orchestrator.get_memory()

    if key not in memory:
        print(
            f"\nNo memory found with key: {key}\n"
        )

        return

    orchestrator.memory.forget(key)

    print(
        f"\nForgot memory: {key}\n"
    )


def main() -> None:
    print_banner()

    orchestrator = Orchestrator()

    while True:
        try:
            user_input = input(
                "You: "
            ).strip()

            if not user_input:
                continue

            command = user_input.lower()

            # ------------------------------------------
            # EXIT
            # ------------------------------------------

            if command == "exit":
                print(
                    "\nShutting down "
                    "V.A.U.L.T. Goodbye."
                )

                break

            # ------------------------------------------
            # HELP
            # ------------------------------------------

            if command == "help":
                print_help()
                continue

            # ------------------------------------------
            # HISTORY
            # ------------------------------------------

            if command == "history":

                history = (
                    orchestrator
                    .get_session_history()
                )

                print()

                if not history:

                    print(
                        "No conversation history "
                        "available."
                    )

                else:

                    print(
                        "Conversation History:"
                    )

                    for message in history:

                        role = message.get(
                            "role",
                            "unknown"
                        )

                        content = message.get(
                            "content",
                            ""
                        )

                        print(
                            f"{role.capitalize()}: "
                            f"{content}"
                        )

                print()

                continue

            # ------------------------------------------
            # CLEAR SESSION
            # ------------------------------------------

            if command == "clear":

                orchestrator.clear_session()

                print(
                    "\nConversation session "
                    "cleared.\n"
                )

                continue

            # ------------------------------------------
            # SHOW MEMORY
            # ------------------------------------------

            if command == "memory":

                print_memory(
                    orchestrator
                )

                continue

            # ------------------------------------------
            # CLEAR ALL MEMORY
            # ------------------------------------------

            if command == "clear memory":

                orchestrator.clear_memory()

                print(
                    "\nAll long-term memory "
                    "has been cleared.\n"
                )

                continue

            # ------------------------------------------
            # FORGET SPECIFIC MEMORY
            # ------------------------------------------

            if command.startswith(
                "forget "
            ):

                memory_key = user_input[
                    len("forget "):
                ].strip()

                forget_memory(
                    orchestrator,
                    memory_key
                )

                continue

            # ------------------------------------------
            # NORMAL AI REQUEST
            # ------------------------------------------

            print(
                "\nV.A.U.L.T. is thinking...\n"
            )

            response = orchestrator.run(
                user_input
            )

            print(
                f"V.A.U.L.T.: {response}\n"
            )

        except KeyboardInterrupt:

            print(
                "\n\nShutting down "
                "V.A.U.L.T. Goodbye."
            )

            break

        except Exception as exc:

            print(
                f"\nSystem Error: {exc}\n"
            )


if __name__ == "__main__":
    main()
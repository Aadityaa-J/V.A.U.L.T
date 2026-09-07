"""
V.A.U.L.T. Interactive Chat Interface

Provides the terminal interface for:

    - Conversation
    - Memory management
    - Model routing information
    - Fine-tuning controls
"""


from agents.orchestrator import Orchestrator


# ==========================================================
# BANNER
# ==========================================================

def print_banner():

    print()

    print("=" * 60)

    print("V.A.U.L.T. AI SYSTEM")

    print("Sovereign Local AI Assistant")

    print("=" * 60)

    print()

    print("Commands:")

    print("  exit              - Close V.A.U.L.T.")

    print("  quit              - Close V.A.U.L.T.")

    print("  clear             - Clear conversation memory")

    print("  memory            - Show persistent memory")

    print("  routing           - Show model routing information")

    print()

    print("Fine-Tuning Commands:")

    print("  finetune status   - Show fine-tuning status")

    print("  finetune on       - Enable training data collection")

    print("  finetune off      - Disable training data collection")

    print("  finetune train    - Manually run fine-tuning")

    print()


# ==========================================================
# PRINT FINE-TUNING STATUS
# ==========================================================

def print_fine_tuning_status(

    vault

):

    print()

    print("=" * 60)

    print("FINE-TUNING STATUS")

    print("=" * 60)

    print()

    try:

        status = (

            vault.get_fine_tuning_status()

        )

    except Exception as error:

        print(

            f"Unable to retrieve fine-tuning status: "

            f"{error}"

        )

        print()

        return

    # ------------------------------------------------------
    # ENABLED
    # ------------------------------------------------------

    enabled = status.get(

        "enabled",

        False,

    )

    print(

        f"Collection Enabled: {enabled}"

    )

    # ------------------------------------------------------
    # LAST ERROR
    # ------------------------------------------------------

    last_error = status.get(

        "last_error"

    )

    if last_error:

        print()

        print(

            "Last Error:"

        )

        print(

            last_error

        )

    # ------------------------------------------------------
    # INTEGRATION
    # ------------------------------------------------------

    integration = status.get(

        "integration",

        {},

    )

    if isinstance(

        integration,

        dict,

    ):

        print()

        print(

            "Interactions: "

            f"{integration.get('total_interactions', 0)}"

        )

        print(

            "Training Examples: "

            f"{integration.get('total_examples_added', 0)}"

        )

        print(

            "Auto Training: "

            f"{integration.get('auto_train', False)}"

        )

        print(

            "Minimum Examples Before Check: "

            f"{integration.get('minimum_examples_before_check', 0)}"

        )

    print()


# ==========================================================
# ENABLE FINE-TUNING
# ==========================================================

def enable_fine_tuning(

    vault

):

    vault.enable_fine_tuning()

    print()

    print(

        "V.A.U.L.T.: Fine-tuning data collection "

        "enabled."

    )

    print()


# ==========================================================
# DISABLE FINE-TUNING
# ==========================================================

def disable_fine_tuning(

    vault

):

    vault.disable_fine_tuning()

    print()

    print(

        "V.A.U.L.T.: Fine-tuning data collection "

        "disabled."

    )

    print()


# ==========================================================
# RUN FINE-TUNING
# ==========================================================

def run_fine_tuning(

    vault

):

    print()

    print(

        "V.A.U.L.T.: Checking fine-tuning pipeline..."

    )

    print()

    try:

        integration = (

            vault.fine_tuning

        )

        result = (

            integration.run_training()

        )

    except Exception as error:

        print(

            "V.A.U.L.T. FINE-TUNING ERROR:"

        )

        print()

        print(

            error

        )

        print()

        return

    # ------------------------------------------------------
    # SUCCESS
    # ------------------------------------------------------

    if result.get(

        "success",

        False,

    ):

        print(

            "Fine-tuning pipeline completed successfully."

        )

    else:

        print(

            "Fine-tuning pipeline did not complete."

        )

    print()

    print(

        "Result:"

    )

    print(

        result

    )

    print()


# ==========================================================
# PRINT ROUTING STATUS
# ==========================================================

def print_routing_status(

    vault

):

    print()

    print("=" * 60)

    print("MODEL ROUTING")

    print("=" * 60)

    print()

    try:

        router = getattr(

            vault,

            "runtime_router",

            None,

        )

        if router is None:

            print(

                "Runtime router status is not "

                "available through the orchestrator."

            )

        else:

            print(

                router.get_status()

            )

    except Exception as error:

        print(

            f"Unable to retrieve routing status: "

            f"{error}"

        )

    print()


# ==========================================================
# MAIN
# ==========================================================

def main():

    print_banner()

    print(

        "Initializing V.A.U.L.T..."

    )

    try:

        vault = Orchestrator()

    except Exception as error:

        print()

        print(

            "ERROR: Failed to initialize V.A.U.L.T."

        )

        print(

            error

        )

        return

    print()

    print(

        "V.A.U.L.T. is ready."

    )

    print(

        "Fine-tuning interaction collection enabled."

    )

    print()

    # ======================================================
    # CHAT LOOP
    # ======================================================

    while True:

        try:

            user_input = (

                input(

                    "YOU: "

                ).strip()

            )

        except KeyboardInterrupt:

            print()

            print()

            print(

                "V.A.U.L.T.: Shutting down."

            )

            break

        except EOFError:

            print()

            print(

                "V.A.U.L.T.: Shutting down."

            )

            break

        # --------------------------------------------------
        # EMPTY INPUT
        # --------------------------------------------------

        if not user_input:

            continue

        command = (

            user_input.lower()

        )

        # --------------------------------------------------
        # EXIT
        # --------------------------------------------------

        if command in {

            "exit",

            "quit",

        }:

            print()

            print(

                "V.A.U.L.T.: Goodbye."

            )

            break

        # --------------------------------------------------
        # CLEAR SESSION
        # --------------------------------------------------

        if command == "clear":

            vault.clear_session()

            print()

            print(

                "V.A.U.L.T.: Conversation "

                "memory cleared."

            )

            print()

            continue

        # --------------------------------------------------
        # SHOW MEMORY
        # --------------------------------------------------

        if command == "memory":

            memory = (

                vault.get_memory()

            )

            print()

            print(

                "PERSISTENT MEMORY"

            )

            print(

                "-" * 40

            )

            if not memory:

                print(

                    "No persistent memory stored."

                )

            else:

                for key, value in (

                    memory.items()

                ):

                    print(

                        f"{key}: {value}"

                    )

            print()

            continue

        # --------------------------------------------------
        # MODEL ROUTING
        # --------------------------------------------------

        if command == "routing":

            print_routing_status(

                vault

            )

            continue

        # --------------------------------------------------
        # FINE-TUNING STATUS
        # --------------------------------------------------

        if command == "finetune status":

            print_fine_tuning_status(

                vault

            )

            continue

        # --------------------------------------------------
        # ENABLE FINE-TUNING
        # --------------------------------------------------

        if command == "finetune on":

            enable_fine_tuning(

                vault

            )

            continue

        # --------------------------------------------------
        # DISABLE FINE-TUNING
        # --------------------------------------------------

        if command == "finetune off":

            disable_fine_tuning(

                vault

            )

            continue

        # --------------------------------------------------
        # MANUAL FINE-TUNING
        # --------------------------------------------------

        if command == "finetune train":

            run_fine_tuning(

                vault

            )

            continue

        # --------------------------------------------------
        # RUN V.A.U.L.T.
        # --------------------------------------------------

        print()

        print(

            "V.A.U.L.T. is thinking..."

        )

        print()

        try:

            response = (

                vault.run(

                    user_input

                )

            )

            print()

            print("=" * 60)

            print(

                "V.A.U.L.T."

            )

            print("=" * 60)

            print()

            print(

                response

            )

            print()

        except Exception as error:

            print()

            print(

                "V.A.U.L.T. ERROR:"

            )

            print()

            print(

                error

            )

            print()


# ==========================================================
# START
# ==========================================================

if __name__ == "__main__":

    main()
"""
V.A.U.L.T. Automatic Fine-Tuning Lifecycle Test

Tests:

Interaction
    ↓
Eligibility
    ↓
Dataset
    ↓
Scheduler
    ↓
Mock Training
    ↓
Evaluation
    ↓
Model Registry
"""


from models.fine_tuning.manager import (
    FineTuningManager
)


def main():

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. AUTOMATIC FINE-TUNING LIFECYCLE TEST"
    )

    print("=" * 60)

    # ==================================================
    # CREATE MANAGER
    # ==================================================

    manager = FineTuningManager()

    # ==================================================
    # SHOW CURRENT DATASET
    # ==================================================

    print()

    print(
        "CURRENT DATASET"
    )

    print("-" * 60)

    print(
        manager.dataset.get_info()
    )

    # ==================================================
    # TEST TRAINING STATUS
    # ==================================================

    print()

    print(
        "TRAINING SCHEDULER STATUS"
    )

    print("-" * 60)

    training_status = (
        manager.check_training_status()
    )

    print(
        training_status
    )

    # ==================================================
    # RUN LIFECYCLE
    # ==================================================

    print()

    print(
        "RUNNING FINE-TUNING LIFECYCLE"
    )

    print("-" * 60)

    evaluation_dataset = [

        {
            "input":
                (
                    "Calculate pump efficiency "
                    "when input power is 10 kW "
                    "and useful power is 8 kW."
                ),

            "expected":
                "80%",

        }

    ]

    result = (
        manager.run_training(

            base_model="qwen3:4b",

            task_type="engineering",

            evaluation_dataset=(
                evaluation_dataset
            ),

        )
    )

    print(
        result
    )

    # ==================================================
    # FINAL DATASET STATUS
    # ==================================================

    print()

    print(
        "FINAL DATASET STATUS"
    )

    print("-" * 60)

    print(
        manager.dataset.get_info()
    )

    # ==================================================
    # REGISTRY STATUS
    # ==================================================

    print()

    print(
        "MODEL REGISTRY STATUS"
    )

    print("-" * 60)

    try:

        print(
            manager.registry.get_models()
        )

    except AttributeError:

        print(
            "Registry does not yet expose "
            "get_models()."
        )

    print()

    print("=" * 60)

    print(
        "FINE-TUNING LIFECYCLE TEST COMPLETE"
    )

    print("=" * 60)


if __name__ == "__main__":

    main()
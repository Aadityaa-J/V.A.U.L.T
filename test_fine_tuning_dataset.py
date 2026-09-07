from models.fine_tuning.dataset import (
    FineTuningDataset
)


print()
print("=" * 60)
print("V.A.U.L.T. FINE-TUNING DATASET TEST")
print("=" * 60)


dataset = FineTuningDataset(
    storage_directory="data/test_fine_tuning"
)


example = {

    "task":
        "Calculate pump efficiency",

    "task_type":
        "engineering",

    "input":
        "Input power is 10 kW and useful hydraulic power is 8 kW.",

    "initial_response":
        "The pump efficiency is 80%.",

    "peer_review": {

        "verdict":
            "PASS",

        "feedback":
            "",

    },

    "human_feedback":
        "",

    "final_response":
        (
            "Pump efficiency = "
            "(8 / 10) × 100 = 80%."
        ),

    "quality":
        "accepted",

    "source_model":
        "qwen3:4b",

    "validation_status":
        "PASS",

}


print()
print("ADDING VALID EXAMPLE")
print("-" * 60)

result = dataset.add_example(
    example
)

print(result)


print()
print("TESTING DUPLICATE DETECTION")
print("-" * 60)

duplicate_result = dataset.add_example(
    example
)

print(duplicate_result)


print()
print("DATASET METADATA")
print("-" * 60)

print(
    dataset.get_metadata()
)


print()
print("STORED EXAMPLES")
print("-" * 60)

examples = (
    dataset.get_examples()
)

print(
    f"Total examples: "
    f"{len(examples)}"
)


print()
print("=" * 60)
print("FINE-TUNING DATASET TEST COMPLETE")
print("=" * 60)
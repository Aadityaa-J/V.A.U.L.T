"""
V.A.U.L.T. Fine-Tuning Data Collector

Collects high-quality interactions from V.A.U.L.T.
and converts them into training examples.

Flow:

    User Request
        ↓
    V.A.U.L.T. Response
        ↓
    Quality Check
        ↓
    Training Example
        ↓
    Dataset Storage

Only useful and successful interactions should
be stored for future fine-tuning.
"""


import json

from datetime import datetime

from pathlib import Path

from typing import Any, Dict, List, Optional


# ==========================================================
# DATA COLLECTOR
# ==========================================================

class FineTuningDataCollector:

    """
    Collect training examples from successful
    V.A.U.L.T. interactions.

    Training examples are stored as JSONL.

    Example:

        {
            "prompt": "...",
            "response": "...",
            "task_type": "engineering"
        }
    """

    def __init__(
        self,
        dataset_path: str = (
            "data/fine_tuning/training_data.jsonl"
        ),
        minimum_response_length: int = 10,
        maximum_response_length: int = 50000,
    ):

        self.dataset_path = Path(
            dataset_path
        )

        self.minimum_response_length = (
            minimum_response_length
        )

        self.maximum_response_length = (
            maximum_response_length
        )

        # Create the dataset directory automatically.

        self.dataset_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ======================================================
    # VALIDATION
    # ======================================================

    def is_valid_example(
        self,
        prompt: Any,
        response: Any,
        task_type: Optional[str] = None,
    ) -> Dict[str, Any]:

        """
        Validate an interaction before storing it
        as a fine-tuning example.
        """

        # --------------------------------------------------
        # PROMPT VALIDATION
        # --------------------------------------------------

        if not isinstance(
            prompt,
            str,
        ):

            return {

                "valid": False,

                "reason":
                    "Prompt must be a string.",

            }

        prompt = prompt.strip()

        if not prompt:

            return {

                "valid": False,

                "reason":
                    "Prompt cannot be empty.",

            }

        # --------------------------------------------------
        # RESPONSE VALIDATION
        # --------------------------------------------------

        if not isinstance(
            response,
            str,
        ):

            return {

                "valid": False,

                "reason":
                    "Response must be a string.",

            }

        response = response.strip()

        if not response:

            return {

                "valid": False,

                "reason":
                    "Response cannot be empty.",

            }

        # --------------------------------------------------
        # RESPONSE LENGTH
        # --------------------------------------------------

        if len(response) < (
            self.minimum_response_length
        ):

            return {

                "valid": False,

                "reason":
                    (
                        "Response is too short "
                        "for training."
                    ),

            }

        if len(response) > (
            self.maximum_response_length
        ):

            return {

                "valid": False,

                "reason":
                    (
                        "Response is too large "
                        "for training."
                    ),

            }

        # --------------------------------------------------
        # ERROR RESPONSE DETECTION
        # --------------------------------------------------

        response_lower = response.lower()

        error_markers = [

            "traceback (most recent call last)",

            "module not found",

            "modulenotfounderror",

            "importerror:",

            "syntaxerror:",

            "v.a.u.l.t. error:",

            "failed to initialize",

        ]

        for marker in error_markers:

            if marker in response_lower:

                return {

                    "valid": False,

                    "reason":
                        (
                            "Response appears to "
                            "contain a system error."
                        ),

                }

        # --------------------------------------------------
        # TASK TYPE VALIDATION
        # --------------------------------------------------

        if task_type is not None:

            if not isinstance(
                task_type,
                str,
            ):

                return {

                    "valid": False,

                    "reason":
                        "Task type must be a string.",

                }

            if not task_type.strip():

                return {

                    "valid": False,

                    "reason":
                        "Task type cannot be empty.",

                }

        # --------------------------------------------------
        # VALID
        # --------------------------------------------------

        return {

            "valid": True,

            "reason":
                "Training example is valid.",

        }

    # ======================================================
    # CREATE EXAMPLE
    # ======================================================

    def create_example(
        self,
        prompt: str,
        response: str,
        task_type: str = "general",
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:

        """
        Create a standardized fine-tuning example.
        """

        validation = self.is_valid_example(
            prompt=prompt,
            response=response,
            task_type=task_type,
        )

        if not validation.get(
            "valid",
            False,
        ):

            return {

                "success": False,

                "reason":
                    validation.get(
                        "reason"
                    ),

                "example": None,

            }

        example = {

            "prompt":
                prompt.strip(),

            "response":
                response.strip(),

            "task_type":
                task_type.strip(),

            "created_at":
                datetime.now()
                .isoformat(),

        }

        # --------------------------------------------------
        # OPTIONAL METADATA
        # --------------------------------------------------

        if metadata is not None:

            if isinstance(
                metadata,
                dict,
            ):

                example[
                    "metadata"
                ] = metadata

        return {

            "success": True,

            "reason":
                (
                    "Training example created "
                    "successfully."
                ),

            "example":
                example,

        }

    # ======================================================
    # DUPLICATE DETECTION
    # ======================================================

    def _is_duplicate(
        self,
        example: Dict[str, Any],
    ) -> bool:

        """
        Check whether an identical prompt-response
        pair already exists in the dataset.
        """

        if not self.dataset_path.exists():

            return False

        try:

            with open(
                self.dataset_path,
                "r",
                encoding="utf-8",
            ) as file:

                for line in file:

                    line = line.strip()

                    if not line:

                        continue

                    try:

                        existing_example = (
                            json.loads(line)
                        )

                    except json.JSONDecodeError:

                        # Ignore corrupted lines rather
                        # than breaking the collector.

                        continue

                    existing_prompt = (
                        existing_example.get(
                            "prompt",
                            ""
                        )
                    )

                    existing_response = (
                        existing_example.get(
                            "response",
                            ""
                        )
                    )

                    if (
                        existing_prompt
                        == example.get("prompt")
                        and
                        existing_response
                        == example.get("response")
                    ):

                        return True

        except Exception:

            # Dataset reading errors should not crash
            # V.A.U.L.T.

            return False

        return False

    # ======================================================
    # STORE EXAMPLE
    # ======================================================

    def store_example(
        self,
        example: Dict[str, Any],
        allow_duplicates: bool = False,
    ) -> Dict[str, Any]:

        """
        Store a training example inside the JSONL
        fine-tuning dataset.
        """

        if not isinstance(
            example,
            dict,
        ):

            return {

                "success": False,

                "stored": False,

                "reason":
                    "Example must be a dictionary.",

            }

        prompt = example.get(
            "prompt"
        )

        response = example.get(
            "response"
        )

        task_type = example.get(
            "task_type",
            "general",
        )

        validation = self.is_valid_example(
            prompt=prompt,
            response=response,
            task_type=task_type,
        )

        if not validation.get(
            "valid",
            False,
        ):

            return {

                "success": False,

                "stored": False,

                "reason":
                    validation.get(
                        "reason"
                    ),

            }

        # --------------------------------------------------
        # DUPLICATE CHECK
        # --------------------------------------------------

        if not allow_duplicates:

            if self._is_duplicate(
                example
            ):

                return {

                    "success": True,

                    "stored": False,

                    "duplicate": True,

                    "reason":
                        (
                            "Training example already "
                            "exists."
                        ),

                    "example":
                        example,

                }

        # --------------------------------------------------
        # WRITE JSONL
        # --------------------------------------------------

        try:

            with open(
                self.dataset_path,
                "a",
                encoding="utf-8",
            ) as file:

                json.dump(
                    example,
                    file,
                    ensure_ascii=False,
                )

                file.write("\n")

        except Exception as exc:

            return {

                "success": False,

                "stored": False,

                "reason":
                    str(exc),

            }

        return {

            "success": True,

            "stored": True,

            "duplicate": False,

            "reason":
                (
                    "Training example stored "
                    "successfully."
                ),

            "example":
                example,

            "dataset_path":
                str(self.dataset_path),

        }

    # ======================================================
    # COLLECT INTERACTION
    # ======================================================

    def collect(
        self,
        prompt: str,
        response: str,
        task_type: str = "general",
        metadata: Optional[
            Dict[str, Any]
        ] = None,
        allow_duplicates: bool = False,
    ) -> Dict[str, Any]:

        """
        Main method.

        Convert a V.A.U.L.T. interaction into a
        training example and store it.
        """

        # --------------------------------------------------
        # CREATE EXAMPLE
        # --------------------------------------------------

        creation_result = (
            self.create_example(
                prompt=prompt,
                response=response,
                task_type=task_type,
                metadata=metadata,
            )
        )

        if not creation_result.get(
            "success",
            False,
        ):

            return {

                "success": False,

                "stored": False,

                "stage":
                    "validation",

                "reason":
                    creation_result.get(
                        "reason"
                    ),

            }

        example = (
            creation_result.get(
                "example"
            )
        )

        # --------------------------------------------------
        # STORE EXAMPLE
        # --------------------------------------------------

        storage_result = (
            self.store_example(
                example=example,
                allow_duplicates=(
                    allow_duplicates
                ),
            )
        )

        storage_result[
            "stage"
        ] = "storage"

        return storage_result

    # ======================================================
    # READ DATASET
    # ======================================================

    def get_examples(
        self,
        task_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:

        """
        Load stored training examples.

        Optional filtering by task type.
        """

        if not self.dataset_path.exists():

            return []

        examples = []

        try:

            with open(
                self.dataset_path,
                "r",
                encoding="utf-8",
            ) as file:

                for line in file:

                    line = line.strip()

                    if not line:

                        continue

                    try:

                        example = json.loads(
                            line
                        )

                    except json.JSONDecodeError:

                        continue

                    # --------------------------------------
                    # TASK FILTER
                    # --------------------------------------

                    if task_type is not None:

                        if (
                            example.get(
                                "task_type"
                            )
                            != task_type
                        ):

                            continue

                    examples.append(
                        example
                    )

                    # --------------------------------------
                    # LIMIT
                    # --------------------------------------

                    if limit is not None:

                        if (
                            len(examples)
                            >= limit
                        ):

                            break

        except Exception:

            return []

        return examples

    # ======================================================
    # COUNT EXAMPLES
    # ======================================================

    def count_examples(
        self,
        task_type: Optional[str] = None,
    ) -> int:

        """
        Count training examples.
        """

        examples = self.get_examples(
            task_type=task_type
        )

        return len(examples)

    # ======================================================
    # DATASET STATISTICS
    # ======================================================

    def get_statistics(
        self,
    ) -> Dict[str, Any]:

        """
        Return dataset statistics.
        """

        examples = self.get_examples()

        task_counts = {}

        for example in examples:

            task_type = example.get(
                "task_type",
                "unknown",
            )

            task_counts[task_type] = (
                task_counts.get(
                    task_type,
                    0,
                )
                + 1
            )

        return {

            "dataset_path":
                str(self.dataset_path),

            "dataset_exists":
                self.dataset_path.exists(),

            "total_examples":
                len(examples),

            "task_types":
                task_counts,

        }

    # ======================================================
    # CLEAR DATASET
    # ======================================================

    def clear_dataset(
        self,
    ) -> Dict[str, Any]:

        """
        Clear all collected training examples.

        Useful for development and testing.
        """

        try:

            with open(
                self.dataset_path,
                "w",
                encoding="utf-8",
            ):
                pass

        except Exception as exc:

            return {

                "success": False,

                "reason":
                    str(exc),

            }

        return {

            "success": True,

            "reason":
                (
                    "Fine-tuning dataset "
                    "cleared successfully."
                ),

            "dataset_path":
                str(self.dataset_path),

        }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING DATA COLLECTOR TEST"
    )

    print("=" * 60)

    # ======================================================
    # CREATE COLLECTOR
    # ======================================================

    collector = (
        FineTuningDataCollector(
            dataset_path=(
                "data/fine_tuning/"
                "test_training_data.jsonl"
            )
        )
    )

    # Clear test data first.

    collector.clear_dataset()

    # ======================================================
    # TEST 1
    # ENGINEERING EXAMPLE
    # ======================================================

    print()

    print(
        "TEST 1: STORE ENGINEERING EXAMPLE"
    )

    print("-" * 60)

    result = collector.collect(

        prompt=(
            "Calculate the force required "
            "to accelerate a 10 kg object "
            "at 5 m/s²."
        ),

        response=(
            "Using Newton's second law, "
            "F = m × a. Therefore, "
            "F = 10 × 5 = 50 N."
        ),

        task_type="engineering",

    )

    print(result)

    # ======================================================
    # TEST 2
    # CODING EXAMPLE
    # ======================================================

    print()

    print(
        "TEST 2: STORE CODING EXAMPLE"
    )

    print("-" * 60)

    result = collector.collect(

        prompt=(
            "Write a Python function "
            "that calculates factorial."
        ),

        response=(
            "def factorial(n):\n"
            "    if n <= 1:\n"
            "        return 1\n"
            "    return n * factorial(n - 1)"
        ),

        task_type="coding",

    )

    print(result)

    # ======================================================
    # TEST 3
    # DUPLICATE DETECTION
    # ======================================================

    print()

    print(
        "TEST 3: DUPLICATE DETECTION"
    )

    print("-" * 60)

    result = collector.collect(

        prompt=(
            "Calculate the force required "
            "to accelerate a 10 kg object "
            "at 5 m/s²."
        ),

        response=(
            "Using Newton's second law, "
            "F = m × a. Therefore, "
            "F = 10 × 5 = 50 N."
        ),

        task_type="engineering",

    )

    print(result)

    # ======================================================
    # TEST 4
    # INVALID RESPONSE
    # ======================================================

    print()

    print(
        "TEST 4: INVALID ERROR RESPONSE"
    )

    print("-" * 60)

    result = collector.collect(

        prompt=(
            "Test prompt"
        ),

        response=(
            "Traceback "
            "(most recent call last)"
        ),

        task_type="general",

    )

    print(result)

    # ======================================================
    # TEST 5
    # COUNT EXAMPLES
    # ======================================================

    print()

    print(
        "TEST 5: EXAMPLE COUNTS"
    )

    print("-" * 60)

    print(

        "Total examples:",

        collector.count_examples()

    )

    print(

        "Engineering examples:",

        collector.count_examples(
            task_type="engineering"
        )

    )

    print(

        "Coding examples:",

        collector.count_examples(
            task_type="coding"
        )

    )

    # ======================================================
    # TEST 6
    # DATASET STATISTICS
    # ======================================================

    print()

    print(
        "TEST 6: DATASET STATISTICS"
    )

    print("-" * 60)

    print(

        collector.get_statistics()

    )

    print()

    print("=" * 60)

    print(
        "DATA COLLECTOR TEST COMPLETE"
    )

    print("=" * 60)
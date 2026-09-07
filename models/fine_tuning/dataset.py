"""
V.A.U.L.T. Fine-Tuning Dataset Manager

Responsible for:

- Storing local training examples
- Validating dataset records
- Preventing duplicates
- Creating versioned datasets
- Maintaining audit metadata

This module is runtime-agnostic.

It does NOT depend on:

- Ollama
- Transformers
- PEFT
- CUDA
- Any specific training framework
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class FineTuningDataset:

    """
    Local dataset manager for V.A.U.L.T.
    automatic fine-tuning.
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
    ):

        if storage_path is None:

            storage_path = (
                "data/fine_tuning"
            )

        self.storage_path = Path(
            storage_path
        )

        self.storage_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.dataset_file = (
            self.storage_path
            / "training_dataset.jsonl"
        )

        self.metadata_file = (
            self.storage_path
            / "dataset_metadata.json"
        )

        self._initialize_metadata()

    # ==========================================================
    # METADATA
    # ==========================================================

    def _initialize_metadata(
        self,
    ) -> None:

        if self.metadata_file.exists():

            return

        metadata = {

            "dataset_version": 1,

            "created_at":
                self._timestamp(),

            "updated_at":
                self._timestamp(),

            "total_examples": 0,

        }

        self._save_metadata(
            metadata
        )

    def _load_metadata(
        self,
    ) -> Dict[str, Any]:

        try:

            with open(
                self.metadata_file,
                "r",
                encoding="utf-8",
            ) as file:

                return json.load(
                    file
                )

        except (
            FileNotFoundError,
            json.JSONDecodeError,
        ):

            return {

                "dataset_version": 1,

                "created_at":
                    self._timestamp(),

                "updated_at":
                    self._timestamp(),

                "total_examples": 0,

            }

    def _save_metadata(
        self,
        metadata: Dict[str, Any],
    ) -> None:

        with open(
            self.metadata_file,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                metadata,
                file,
                indent=4,
                ensure_ascii=False,
            )

    # ==========================================================
    # ADD EXAMPLE
    # ==========================================================

    def add_example(
        self,
        example: Dict[str, Any],
    ) -> Dict[str, Any]:

        """
        Validate and store a training example.

        Returns information about whether
        the example was added.
        """

        validation = (
            self.validate_example(
                example
            )
        )

        if not validation["valid"]:

            return {

                "success": False,

                "reason":
                    validation["reason"],

            }

        record = dict(
            example
        )

        # ------------------------------------------------------
        # ADD ID
        # ------------------------------------------------------

        record_id = (
            self._generate_id(
                record
            )
        )

        record["id"] = (
            record_id
        )

        # ------------------------------------------------------
        # ADD TIMESTAMP
        # ------------------------------------------------------

        if "timestamp" not in record:

            record["timestamp"] = (
                self._timestamp()
            )

        # ------------------------------------------------------
        # CHECK DUPLICATE
        # ------------------------------------------------------

        if self.has_duplicate(
            record_id
        ):

            return {

                "success": False,

                "reason":
                    "Duplicate training example.",

                "id":
                    record_id,

            }

        # ------------------------------------------------------
        # STORE RECORD
        # ------------------------------------------------------

        with open(
            self.dataset_file,
            "a",
            encoding="utf-8",
        ) as file:

            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

        # ------------------------------------------------------
        # UPDATE METADATA
        # ------------------------------------------------------

        metadata = (
            self._load_metadata()
        )

        metadata[
            "total_examples"
        ] += 1

        metadata[
            "updated_at"
        ] = self._timestamp()

        self._save_metadata(
            metadata
        )

        return {

            "success": True,

            "id": record_id,

            "dataset_version":
                metadata[
                    "dataset_version"
                ],

        }

    # ==========================================================
    # VALIDATE EXAMPLE
    # ==========================================================

    def validate_example(
        self,
        example: Any,
    ) -> Dict[str, Any]:

        """
        Validate a training example.
        """

        if not isinstance(
            example,
            dict,
        ):

            return {

                "valid": False,

                "reason":
                    "Training example must be a dictionary.",

            }

        required_fields = [

            "task",

            "task_type",

            "input",

            "final_response",

            "quality",

        ]

        for field in required_fields:

            value = example.get(
                field
            )

            if not isinstance(
                value,
                str,
            ):

                return {

                    "valid": False,

                    "reason":
                        f"Missing or invalid field: "
                        f"{field}",

                }

            if not value.strip():

                return {

                    "valid": False,

                    "reason":
                        f"Field cannot be empty: "
                        f"{field}",

                }

        return {

            "valid": True,

            "reason": None,

        }

    # ==========================================================
    # DUPLICATE CHECK
    # ==========================================================

    def has_duplicate(
        self,
        record_id: str,
    ) -> bool:

        if not self.dataset_file.exists():

            return False

        with open(
            self.dataset_file,
            "r",
            encoding="utf-8",
        ) as file:

            for line in file:

                line = line.strip()

                if not line:

                    continue

                try:

                    record = json.loads(
                        line
                    )

                except json.JSONDecodeError:

                    continue

                if record.get(
                    "id"
                ) == record_id:

                    return True

        return False

    # ==========================================================
    # LOAD EXAMPLES
    # ==========================================================

    def get_examples(
        self,
    ) -> List[Dict[str, Any]]:

        """
        Return all stored training examples.
        """

        examples = []

        if not self.dataset_file.exists():

            return examples

        with open(
            self.dataset_file,
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

                    examples.append(
                        example
                    )

                except json.JSONDecodeError:

                    continue

        return examples

    # ==========================================================
    # DATASET COUNT
    # ==========================================================

    def count_examples(
        self,
    ) -> int:

        return len(
            self.get_examples()
        )

    # ==========================================================
    # CREATE DATASET VERSION
    # ==========================================================

    def create_new_version(
        self,
    ) -> int:

        """
        Increment the dataset version.
        """

        metadata = (
            self._load_metadata()
        )

        metadata[
            "dataset_version"
        ] += 1

        metadata[
            "updated_at"
        ] = self._timestamp()

        self._save_metadata(
            metadata
        )

        return metadata[
            "dataset_version"
        ]

    # ==========================================================
    # DATASET INFO
    # ==========================================================

    def get_info(
        self,
    ) -> Dict[str, Any]:

        metadata = (
            self._load_metadata()
        )

        return {

            "dataset_version":
                metadata.get(
                    "dataset_version",
                    1,
                ),

            "total_examples":
                self.count_examples(),

            "created_at":
                metadata.get(
                    "created_at"
                ),

            "updated_at":
                metadata.get(
                    "updated_at"
                ),

            "storage_path":
                str(
                    self.storage_path
                ),

        }

    # ==========================================================
    # GENERATE RECORD ID
    # ==========================================================

    def _generate_id(
        self,
        record: Dict[str, Any],
    ) -> str:

        """
        Generate a deterministic ID.

        Identical records will generate the same ID,
        allowing duplicate detection.
        """

        id_fields = {

            "task":
                record.get(
                    "task",
                    "",
                ),

            "task_type":
                record.get(
                    "task_type",
                    "",
                ),

            "input":
                record.get(
                    "input",
                    "",
                ),

            "final_response":
                record.get(
                    "final_response",
                    "",
                ),

        }

        serialized = json.dumps(

            id_fields,

            sort_keys=True,

            ensure_ascii=False,

        )

        return hashlib.sha256(

            serialized.encode(
                "utf-8"
            )

        ).hexdigest()

    # ==========================================================
    # TIMESTAMP
    # ==========================================================

    def _timestamp(
        self,
    ) -> str:

        return datetime.now().isoformat()


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    dataset = FineTuningDataset()

    example = {

        "task":
            "Calculate pump efficiency",

        "task_type":
            "engineering",

        "input":
            "Input power is 10 kW and useful hydraulic power is 8 kW.",

        "initial_response":
            "Pump efficiency is 80%.",

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
                "Efficiency = 8 / 10 = "
                "0.8 = 80%."
            ),

        "quality":
            "accepted",

        "source_model":
            "qwen3:4b",

    }

    result = dataset.add_example(
        example
    )

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING DATASET TEST"
    )

    print("=" * 60)

    print()

    print(
        "ADD RESULT:"
    )

    print(
        result
    )

    print()

    print(
        "DATASET INFO:"
    )

    print(
        dataset.get_info()
    )

    print()

    print("=" * 60)
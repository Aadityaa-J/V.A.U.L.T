import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional


class AgentMemory:
    """
    Stores important facts extracted from conversations.

    Memory is persisted to disk and each memory item includes:
    - value
    - category
    - importance
    - created_at
    - updated_at
    """

    def __init__(
        self,
        memory_file: str = "data/memory.json"
    ):
        self.memory_file = Path(memory_file)
        self.facts: Dict[str, Dict[str, Any]] = {}

        self._load()

    def _current_timestamp(self) -> str:
        """
        Return the current UTC timestamp.
        """

        return datetime.now(
            timezone.utc
        ).isoformat()

    def _load(self) -> None:
        """
        Load memory from disk.

        Supports older memory formats automatically.
        """

        if not self.memory_file.exists():
            return

        try:
            with open(
                self.memory_file,
                "r",
                encoding="utf-8"
            ) as file:
                data = json.load(file)

            if not isinstance(data, dict):
                return

            converted_facts = {}

            for key, value in data.items():

                timestamp = (
                    self._current_timestamp()
                )

                # --------------------------------------
                # STRUCTURED MEMORY
                # --------------------------------------

                if (
                    isinstance(value, dict)
                    and "value" in value
                ):

                    converted_facts[key] = {
                        "value": value.get("value"),

                        "category": value.get(
                            "category",
                            "general"
                        ),

                        "importance": value.get(
                            "importance",
                            5
                        ),

                        "created_at": value.get(
                            "created_at",
                            timestamp
                        ),

                        "updated_at": value.get(
                            "updated_at",
                            timestamp
                        ),
                    }

                # --------------------------------------
                # OLD MEMORY FORMAT
                # --------------------------------------

                else:

                    converted_facts[key] = {
                        "value": value,

                        "category": "general",

                        "importance": 5,

                        "created_at": timestamp,

                        "updated_at": timestamp,
                    }

            self.facts = converted_facts

            # Automatically upgrade old memory files.
            self._save()

        except (
            json.JSONDecodeError,
            OSError
        ):

            self.facts = {}

    def _save(self) -> None:
        """
        Save memory to disk.
        """

        try:

            self.memory_file.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            with open(
                self.memory_file,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    self.facts,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

        except OSError as exc:

            raise RuntimeError(
                f"Failed to save memory: {exc}"
            )

    def remember(
        self,
        key: str,
        value: Any,
        category: str = "general",
        importance: int = 5
    ) -> None:
        """
        Store or update a memory fact.

        importance must be between 1 and 10.
        """

        if not isinstance(key, str):

            raise TypeError(
                "Memory key must be a string."
            )

        key = key.strip()

        if not key:

            raise ValueError(
                "Memory key cannot be empty."
            )

        if not isinstance(category, str):

            raise TypeError(
                "Memory category must be a string."
            )

        category = category.strip().lower()

        if not category:

            category = "general"

        if not isinstance(importance, int):

            raise TypeError(
                "Memory importance must be an integer."
            )

        if importance < 1 or importance > 10:

            raise ValueError(
                "Memory importance must be "
                "between 1 and 10."
            )

        timestamp = self._current_timestamp()

        # ------------------------------------------
        # UPDATE EXISTING MEMORY
        # ------------------------------------------

        if key in self.facts:

            self.facts[key]["value"] = value

            self.facts[key]["category"] = (
                category
            )

            self.facts[key]["importance"] = (
                importance
            )

            self.facts[key]["updated_at"] = (
                timestamp
            )

        # ------------------------------------------
        # CREATE NEW MEMORY
        # ------------------------------------------

        else:

            self.facts[key] = {
                "value": value,
                "category": category,
                "importance": importance,
                "created_at": timestamp,
                "updated_at": timestamp,
            }

        self._save()

    def recall(
        self,
        key: str,
        default: Optional[Any] = None
    ) -> Any:
        """
        Retrieve only the value of a memory item.
        """

        memory = self.facts.get(key)

        if memory is None:

            return default

        return memory.get(
            "value",
            default
        )

    def get_metadata(
        self,
        key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Return complete metadata for one memory.
        """

        memory = self.facts.get(key)

        if memory is None:

            return None

        return memory.copy()

    def forget(
        self,
        key: str
    ) -> None:
        """
        Remove one memory.
        """

        if key in self.facts:

            del self.facts[key]

            self._save()

    def clear(self) -> None:
        """
        Clear all stored memories.
        """

        self.facts.clear()

        self._save()

    def get_all(self) -> Dict[str, Any]:
        """
        Return only memory values.

        Keeps compatibility with the rest of V.A.U.L.T.
        """

        return {
            key: memory.get("value")
            for key, memory in self.facts.items()
        }

    def get_all_metadata(
        self
    ) -> Dict[str, Dict[str, Any]]:
        """
        Return all memories including metadata.
        """

        return {
            key: value.copy()
            for key, value in self.facts.items()
        }

    def get_by_category(
        self,
        category: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Return memories belonging to a category.
        """

        if not isinstance(category, str):

            raise TypeError(
                "Category must be a string."
            )

        category = category.strip().lower()

        return {
            key: memory.copy()

            for key, memory
            in self.facts.items()

            if memory.get(
                "category"
            ) == category
        }

    def get_important_memories(
        self,
        minimum_importance: int = 7
    ) -> Dict[str, Dict[str, Any]]:
        """
        Return memories with importance greater
        than or equal to the specified value.
        """

        if not isinstance(
            minimum_importance,
            int
        ):

            raise TypeError(
                "Minimum importance must "
                "be an integer."
            )

        return {
            key: memory.copy()

            for key, memory
            in self.facts.items()

            if memory.get(
                "importance",
                0
            ) >= minimum_importance
        }

    def to_prompt(self) -> str:
        """
        Convert memory into text suitable
        for the LLM prompt.
        """

        if not self.facts:

            return "No stored memory."

        # Sort important memories first.
        sorted_memories = sorted(
            self.facts.items(),

            key=lambda item: (
                item[1].get(
                    "importance",
                    0
                )
            ),

            reverse=True
        )

        lines = []

        for key, memory in sorted_memories:

            value = memory.get(
                "value"
            )

            category = memory.get(
                "category",
                "general"
            )

            importance = memory.get(
                "importance",
                5
            )

            readable_key = (
                key.replace(
                    "_",
                    " "
                ).capitalize()
            )

            lines.append(
                f"{readable_key}: {value} "
                f"[Category: {category}, "
                f"Importance: {importance}/10]"
            )

        return "\n".join(lines)
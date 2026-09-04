import re
from typing import Dict, Any

from agents.memory import AgentMemory


class MemoryManager:
    """
    Detects useful personal facts from user messages
    and stores them in persistent AgentMemory.
    """

    def __init__(
        self,
        memory: AgentMemory
    ):
        self.memory = memory

    def process(
        self,
        message: str
    ) -> Dict[str, Any]:
        """
        Analyze a user message and store any useful
        facts that can be reliably extracted.

        Returns the facts that were stored.
        """

        if not isinstance(message, str):
            raise TypeError(
                "Message must be a string."
            )

        stored_facts = {}

        message = message.strip()

        if not message:
            return stored_facts

        # ------------------------------------------
        # NAME
        # ------------------------------------------

        name = self._extract_name(message)

        if name:
            self.memory.remember(
                "user_name",
                name
            )

            stored_facts["user_name"] = name

        # ------------------------------------------
        # FAVORITE COLOR
        # ------------------------------------------

        favorite_color = (
            self._extract_favorite_color(message)
        )

        if favorite_color:
            self.memory.remember(
                "favorite_color",
                favorite_color
            )

            stored_facts[
                "favorite_color"
            ] = favorite_color

        # ------------------------------------------
        # LOCATION
        # ------------------------------------------

        location = self._extract_location(message)

        if location:
            self.memory.remember(
                "location",
                location
            )

            stored_facts["location"] = location

        # ------------------------------------------
        # JOB / OCCUPATION
        # ------------------------------------------

        occupation = (
            self._extract_occupation(message)
        )

        if occupation:
            self.memory.remember(
                "occupation",
                occupation
            )

            stored_facts[
                "occupation"
            ] = occupation

        # ------------------------------------------
        # FAVORITE PROGRAMMING LANGUAGE
        # ------------------------------------------

        favorite_language = (
            self._extract_favorite_language(message)
        )

        if favorite_language:
            self.memory.remember(
                "favorite_programming_language",
                favorite_language
            )

            stored_facts[
                "favorite_programming_language"
            ] = favorite_language

        return stored_facts

    def _extract_name(
        self,
        message: str
    ):
        """
        Extract a user's name from statements such as:

        My name is Alex.
        Remember my name is Alex.
        """

        pattern = re.compile(
            r"^\s*(?:remember\s+)?"
            r"my\s+name\s+is\s+"
            r"([A-Za-z][A-Za-z'-]*)"
            r"\s*[.!?]?\s*$",
            re.IGNORECASE
        )

        match = pattern.match(message)

        if not match:
            return None

        return match.group(1).strip()

    def _extract_favorite_color(
        self,
        message: str
    ):
        """
        Extract favorite color.
        """

        pattern = re.compile(
            r"^\s*(?:my\s+)?"
            r"(?:favorite|favourite)"
            r"\s+color\s+is\s+"
            r"([A-Za-z]+)"
            r"\s*[.!?]?\s*$",
            re.IGNORECASE
        )

        match = pattern.match(message)

        if not match:
            return None

        return match.group(1).strip()

    def _extract_location(
        self,
        message: str
    ):
        """
        Extract location from statements such as:

        I live in Tokyo.
        I live in Japan.
        """

        pattern = re.compile(
            r"^\s*i\s+live\s+in\s+"
            r"(.+?)"
            r"\s*[.!?]?\s*$",
            re.IGNORECASE
        )

        match = pattern.match(message)

        if not match:
            return None

        location = match.group(1).strip()

        if not location:
            return None

        return location

    def _extract_occupation(
        self,
        message: str
    ):
        """
        Extract occupation from statements such as:

        I am a software developer.
        I'm a student.
        """

        pattern = re.compile(
            r"^\s*i(?:\s+am|'m)\s+(?:a|an)\s+"
            r"(.+?)"
            r"\s*[.!?]?\s*$",
            re.IGNORECASE
        )

        match = pattern.match(message)

        if not match:
            return None

        occupation = match.group(1).strip()

        if not occupation:
            return None

        return occupation

    def _extract_favorite_language(
        self,
        message: str
    ):
        """
        Extract favorite programming language.

        Example:

        My favorite programming language is Python.
        """

        pattern = re.compile(
            r"^\s*(?:my\s+)?"
            r"(?:favorite|favourite)"
            r"\s+programming\s+language\s+is\s+"
            r"(.+?)"
            r"\s*[.!?]?\s*$",
            re.IGNORECASE
        )

        match = pattern.match(message)

        if not match:
            return None

        language = match.group(1).strip()

        if not language:
            return None

        return language
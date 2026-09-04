from typing import Dict, List, Any


class AgentSession:
    """
    Stores conversation history and shared session context
    for V.A.U.L.T.

    This is intentionally kept simple so that it can later
    be extended with persistent storage, databases, or
    long-term memory.
    """

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []

    def add_user_message(
        self,
        content: str
    ) -> None:
        """
        Add a user message to the session.
        """

        if not isinstance(content, str):
            raise TypeError(
                "User message content must be a string."
            )

        self.messages.append({
            "role": "user",
            "content": content
        })

    def add_assistant_message(
        self,
        content: str
    ) -> None:
        """
        Add an assistant response to the session.
        """

        if not isinstance(content, str):
            raise TypeError(
                "Assistant message content must be a string."
            )

        self.messages.append({
            "role": "assistant",
            "content": content
        })

    def get_messages(self) -> List[Dict[str, Any]]:
        """
        Return a copy of the conversation history.
        """

        return self.messages.copy()

    def get_recent_messages(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Return the most recent messages.
        """

        if limit <= 0:
            raise ValueError(
                "Message limit must be greater than zero."
            )

        return self.messages[-limit:]

    def clear(self) -> None:
        """
        Clear all messages from the session.
        """

        self.messages.clear()

    def to_dict(self) -> Dict[str, Any]:
        """
        Return the session as a serializable dictionary.
        """

        return {
            "messages": self.get_messages()
        }
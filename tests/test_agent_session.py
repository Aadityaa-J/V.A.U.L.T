from agents.session import AgentSession


def main():
    print("=" * 60)
    print("AGENT SESSION TEST")
    print("=" * 60)

    session = AgentSession()

    # --------------------------------------------------
    # TEST 1: EMPTY SESSION
    # --------------------------------------------------

    print("\nTEST 1: EMPTY SESSION")

    messages = session.get_messages()

    print(messages)

    assert messages == []

    print("PASSED")

    # --------------------------------------------------
    # TEST 2: ADD USER MESSAGE
    # --------------------------------------------------

    print("\nTEST 2: USER MESSAGE")

    session.add_user_message(
        "Hello V.A.U.L.T."
    )

    messages = session.get_messages()

    print(messages)

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello V.A.U.L.T."

    print("PASSED")

    # --------------------------------------------------
    # TEST 3: ADD ASSISTANT MESSAGE
    # --------------------------------------------------

    print("\nTEST 3: ASSISTANT MESSAGE")

    session.add_assistant_message(
        "Hello. How can I help you?"
    )

    messages = session.get_messages()

    print(messages)

    assert len(messages) == 2
    assert messages[1]["role"] == "assistant"

    print("PASSED")

    # --------------------------------------------------
    # TEST 4: RECENT MESSAGES
    # --------------------------------------------------

    print("\nTEST 4: RECENT MESSAGES")

    session.add_user_message("Message 3")
    session.add_assistant_message("Message 4")
    session.add_user_message("Message 5")

    recent = session.get_recent_messages(
        limit=2
    )

    print(recent)

    assert len(recent) == 2
    assert recent[0]["content"] == "Message 4"
    assert recent[1]["content"] == "Message 5"

    print("PASSED")

    # --------------------------------------------------
    # TEST 5: SERIALIZATION
    # --------------------------------------------------

    print("\nTEST 5: TO DICT")

    data = session.to_dict()

    print(data)

    assert "messages" in data
    assert len(data["messages"]) == 5

    print("PASSED")

    # --------------------------------------------------
    # TEST 6: CLEAR
    # --------------------------------------------------

    print("\nTEST 6: CLEAR SESSION")

    session.clear()

    messages = session.get_messages()

    print(messages)

    assert messages == []

    print("PASSED")

    print("\n" + "=" * 60)
    print("ALL AGENT SESSION TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
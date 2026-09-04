from agents.agent_loop import AgentLoop


def main():
    print("=" * 60)
    print("AGENT LOOP CONVERSATION HISTORY TEST")
    print("=" * 60)

    conversation_history = [
        {
            "role": "user",
            "content": "My name is Alex."
        },
        {
            "role": "assistant",
            "content": "Nice to meet you, Alex."
        },
    ]

    loop = AgentLoop(
        system_prompt="You are a test agent.",
        model="test-model",
        tools={},
        conversation_history=conversation_history
    )

    state = {
        "task": "What is my name?",
        "observations": [],
        "steps": [],
    }

    prompt = loop._build_prompt(state)

    print("\nGENERATED PROMPT:\n")
    print(prompt)

    # --------------------------------------------------
    # TEST 1: HISTORY EXISTS
    # --------------------------------------------------

    assert "Previous conversation:" in prompt

    print("\nTEST 1 PASSED")

    # --------------------------------------------------
    # TEST 2: USER HISTORY
    # --------------------------------------------------

    assert "USER: My name is Alex." in prompt

    print("TEST 2 PASSED")

    # --------------------------------------------------
    # TEST 3: ASSISTANT HISTORY
    # --------------------------------------------------

    assert (
        "ASSISTANT: Nice to meet you, Alex."
        in prompt
    )

    print("TEST 3 PASSED")

    # --------------------------------------------------
    # TEST 4: CURRENT TASK
    # --------------------------------------------------

    assert "Current user task:" in prompt

    assert "What is my name?" in prompt

    print("TEST 4 PASSED")

    print("\n" + "=" * 60)
    print("CONVERSATION HISTORY TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
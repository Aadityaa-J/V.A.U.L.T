from agents.memory import AgentMemory


def main():
    print("=" * 60)
    print("AGENT MEMORY TEST")
    print("=" * 60)

    memory = AgentMemory()

    print("\nTEST 1: EMPTY MEMORY")

    print(
        "Memory:",
        memory.get_all()
    )

    assert memory.get_all() == {}

    print("PASSED")


    print("\nTEST 2: REMEMBER FACT")

    memory.remember(
        "user_name",
        "Alex"
    )

    result = memory.recall(
        "user_name"
    )

    print(
        "Remembered name:",
        result
    )

    assert result == "Alex"

    print("PASSED")


    print("\nTEST 3: UPDATE FACT")

    memory.remember(
        "user_name",
        "Hirok"
    )

    result = memory.recall(
        "user_name"
    )

    print(
        "Updated name:",
        result
    )

    assert result == "Hirok"

    print("PASSED")


    print("\nTEST 4: DEFAULT VALUE")

    result = memory.recall(
        "unknown_fact",
        "Not found"
    )

    print(
        "Result:",
        result
    )

    assert result == "Not found"

    print("PASSED")


    print("\nTEST 5: FORGET FACT")

    memory.forget(
        "user_name"
    )

    result = memory.recall(
        "user_name"
    )

    print(
        "Result after forgetting:",
        result
    )

    assert result is None

    print("PASSED")


    print("\nTEST 6: MULTIPLE FACTS")

    memory.remember(
        "user_name",
        "Alex"
    )

    memory.remember(
        "favorite_language",
        "Python"
    )

    memory.remember(
        "system_name",
        "V.A.U.L.T."
    )

    facts = memory.get_all()

    print(
        "Stored facts:",
        facts
    )

    assert facts["user_name"] == "Alex"
    assert facts["favorite_language"] == "Python"
    assert facts["system_name"] == "V.A.U.L.T."

    print("PASSED")


    print("\nTEST 7: MEMORY PROMPT")

    prompt = memory.to_prompt()

    print("\nGenerated prompt:")
    print("-" * 60)
    print(prompt)
    print("-" * 60)

    assert "User name: Alex" in prompt
    assert "Favorite language: Python" in prompt

    print("PASSED")


    print("\nTEST 8: CLEAR MEMORY")

    memory.clear()

    print(
        "Memory after clear:",
        memory.get_all()
    )

    assert memory.get_all() == {}

    print("PASSED")


    print("\n" + "=" * 60)
    print("ALL AGENT MEMORY TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
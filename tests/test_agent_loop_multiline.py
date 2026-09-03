from agents.agent_loop import AgentLoop


def main():
    print("=" * 60)
    print("AGENT LOOP MULTILINE PARSER TEST")
    print("=" * 60)

    loop = AgentLoop(
        system_prompt="You are a test agent.",
        model="test-model"
    )

    print("\nTEST 1: MULTILINE TOOL ARGUMENTS")

    tool_response = """
ACTION: tool
NAME: run_python
ARGUMENTS:
numbers = [1, 2, 3, 4, 5]
total = sum(numbers)
print(total)
"""

    action = loop._parse_action(tool_response)

    print(action)

    assert action["type"] == "tool"
    assert action["name"] == "run_python"
    assert "numbers = [1, 2, 3, 4, 5]" in action["arguments"]
    assert "total = sum(numbers)" in action["arguments"]
    assert "print(total)" in action["arguments"]

    print("PASSED")

    print("\nTEST 2: INLINE TOOL ARGUMENTS")

    inline_tool_response = """
ACTION: tool
NAME: calculate
ARGUMENTS: 125 * 8
"""

    action = loop._parse_action(
        inline_tool_response
    )

    print(action)

    assert action["type"] == "tool"
    assert action["name"] == "calculate"
    assert action["arguments"] == "125 * 8"

    print("PASSED")

    print("\nTEST 3: MULTILINE FINAL CONTENT")

    final_response = """
ACTION: final
CONTENT:
The calculation was completed successfully.

The final result is 55.

No errors occurred.
"""

    action = loop._parse_action(final_response)

    print(action)

    assert action["type"] == "final"
    assert "completed successfully" in action["content"]
    assert "final result is 55" in action["content"]
    assert "No errors occurred" in action["content"]

    print("PASSED")

    print("\nTEST 4: INLINE FINAL CONTENT")

    inline_final_response = """
ACTION: final
CONTENT: The answer is 100.
"""

    action = loop._parse_action(
        inline_final_response
    )

    print(action)

    assert action["type"] == "final"
    assert action["content"] == "The answer is 100."

    print("PASSED")

    print("\n" + "=" * 60)
    print("ALL MULTILINE PARSER TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
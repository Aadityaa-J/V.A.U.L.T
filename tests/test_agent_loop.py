from agents.agent_loop import AgentLoop


def main():
    print("=" * 60)
    print("AGENT LOOP ACTION PARSER TEST")
    print("=" * 60)

    loop = AgentLoop(
        system_prompt="Test agent",
        model="qwen3:1.7b"
    )

    final_response = """
ACTION: final
CONTENT: The task has been completed successfully.
"""

    final_action = loop._parse_action(final_response)

    print("\nFINAL ACTION:")
    print(final_action)

    assert final_action["type"] == "final"
    assert (
        final_action["content"]
        == "The task has been completed successfully."
    )

    tool_response = """
Some additional reasoning text.

ACTION: tool
NAME: calculate
ARGUMENTS: 25 * 4
"""

    tool_action = loop._parse_action(tool_response)

    print("\nTOOL ACTION:")
    print(tool_action)

    assert tool_action["type"] == "tool"
    assert tool_action["name"] == "calculate"
    assert tool_action["arguments"] == "25 * 4"

    print("\n" + "=" * 60)
    print("PARSER TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
from agents.agent_loop import AgentLoop


def main():
    print("=" * 60)
    print("AGENT LOOP JSON ARGUMENT TEST")
    print("=" * 60)

    loop = AgentLoop(
        system_prompt="You are a test agent.",
        model="test-model"
    )

    # ==================================================
    # TEST 1: NORMAL JSON
    # ==================================================

    print("\nTEST 1: NORMAL JSON")

    arguments = """
{
    "source": "file1.txt",
    "destination": "folder/file1.txt"
}
"""

    result = loop._normalize_tool_arguments(
        arguments
    )

    print(result)

    assert '"source"' in result
    assert '"destination"' in result

    print("PASSED")

    # ==================================================
    # TEST 2: MARKDOWN JSON
    # ==================================================

    print("\nTEST 2: MARKDOWN JSON")

    arguments = """
                ```json
                {
                    "source": "file1.txt",
                    "destination": "folder/file1.txt"
                }
                ```
                """
    "source": "file1.txt",
    "destination": "folder/file1.txt"
}
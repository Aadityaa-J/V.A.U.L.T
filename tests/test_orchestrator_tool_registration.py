from agents.orchestrator import Orchestrator


def main():
    print("=" * 60)
    print("ORCHESTRATOR TOOL REGISTRATION TEST")
    print("=" * 60)

    orchestrator = Orchestrator()

    expected_tools = [
        "calculate",
        "run_python",

        "list_files",
        "list_directory",
        "file_exists",
        "create_directory",
        "copy_file",
        "move_file",

        "read_document",
        "document_info",
        "search_document",
        "document_summary",
    ]

    print("\nREGISTERED TOOLS:")

    for tool_name in expected_tools:
        exists = orchestrator.tool_registry.has(tool_name)

        print(
            f"{tool_name}: {exists}"
        )

        assert exists is True

    print("\n" + "-" * 60)
    print("AGENT TOOL ASSIGNMENTS")
    print("-" * 60)

    for agent_name in [
        "document",
        "coding",
        "engineering",
    ]:
        tools = orchestrator._get_agent_tools(
            agent_name
        )

        print(
            f"\n{agent_name.upper()} AGENT:"
        )

        print(list(tools.keys()))

        assert len(tools) > 0

    print("\n" + "=" * 60)
    print("ORCHESTRATOR TOOL REGISTRATION TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
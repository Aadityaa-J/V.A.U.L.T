from agents.orchestrator import Orchestrator
from agents.context import AgentContext
from tools.base import BaseTool
from tools.registry import ToolRegistry


class FakeTool(BaseTool):
    name = "fake_tool"
    description = "A fake tool used for integration testing."

    def execute(self, arguments):
        return {
            "status": "success",
            "arguments": arguments
        }


def test_tool_registry_contract():
    registry = ToolRegistry()

    tool = FakeTool()

    registry.register(tool)

    assert registry.has("fake_tool")
    assert registry.get("fake_tool") is tool

    all_tools = registry.get_all()

    assert "fake_tool" in all_tools
    assert all_tools["fake_tool"] is tool


def test_agent_context_contract():
    context = AgentContext(
        task="Test integration contract"
    )

    context.set_metadata(
        "source",
        "integration_test"
    )

    context.add_observation(
        {
            "type": "test_result",
            "value": 42
        }
    )

    context.add_step(
        step_number=1,
        action={
            "type": "tool",
            "name": "fake_tool",
            "arguments": "test"
        },
        observation={
            "type": "tool_result",
            "value": 42
        }
    )

    state = context.to_dict()

    assert state["task"] == (
        "Test integration contract"
    )

    assert state["metadata"]["source"] == (
        "integration_test"
    )

    assert len(state["observations"]) == 1
    assert len(state["steps"]) == 1


def test_orchestrator_exposes_expected_agents():
    orchestrator = Orchestrator()

    assert "document" in orchestrator.agents
    assert "coding" in orchestrator.agents
    assert "engineering" in orchestrator.agents


def test_orchestrator_tool_contract():
    orchestrator = Orchestrator()

    tool = FakeTool()

    orchestrator.register_tool(tool)

    assert orchestrator.tool_registry.has(
        "fake_tool"
    )

    assert orchestrator.tool_registry.get(
        "fake_tool"
    ) is tool


def test_agent_tool_mapping_contract():
    orchestrator = Orchestrator()

    expected_mapping = {
        "document": {
            "read_file",
            "search_knowledge",
            "analyze_image",
            "create_docx",
        },
        "coding": {
            "read_file",
            "write_file",
            "execute_code",
        },
        "engineering": {
            "search_knowledge",
            "calculate",
            "create_xlsx",
        },
    }

    for agent_type, expected_tools in (
        expected_mapping.items()
    ):
        assert agent_type in orchestrator.agent_tools

        actual_tools = set(
            orchestrator.agent_tools[agent_type]
        )

        assert actual_tools == expected_tools


if __name__ == "__main__":
    test_tool_registry_contract()
    test_agent_context_contract()
    test_orchestrator_exposes_expected_agents()
    test_orchestrator_tool_contract()
    test_agent_tool_mapping_contract()

    print(
        "All integration contract tests passed."
    )
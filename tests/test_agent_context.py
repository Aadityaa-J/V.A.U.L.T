from agents.context import AgentContext


def main():
    print("=" * 60)
    print("AGENT CONTEXT TEST")
    print("=" * 60)

    context = AgentContext(
        task="Test an industrial calculation."
    )

    context.add_observation({
        "type": "tool_result",
        "tool": "calculate",
        "result": "100"
    })

    context.add_step(
        step_number=1,
        action={
            "type": "tool",
            "name": "calculate",
            "arguments": "50 * 2"
        },
        observation={
            "type": "tool_result",
            "tool": "calculate",
            "result": "100"
        }
    )

    context.set_metadata(
        "agent",
        "Engineering Agent"
    )

    print("\nCONTEXT:")
    print(context.to_dict())

    assert context.task == (
        "Test an industrial calculation."
    )

    assert len(context.observations) == 1

    assert len(context.steps) == 1

    assert (
        context.get_metadata("agent")
        == "Engineering Agent"
    )

    data = context.to_dict()

    assert data["task"] == (
        "Test an industrial calculation."
    )

    assert len(data["observations"]) == 1

    assert len(data["steps"]) == 1

    print("\n" + "=" * 60)
    print("AGENT CONTEXT TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
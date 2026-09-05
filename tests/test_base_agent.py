from agents.base import BaseAgent


def main():
    print("=" * 60)
    print("BASE AGENT TEST")
    print("=" * 60)

    agent = BaseAgent(
        name="Test Agent",
        task_type="general",
        system_prompt=(
            "You are a test agent. "
            "Identify yourself as a test agent."
        )
    )

    result = agent.run(
        "Say hello and identify yourself as a test agent."
    )

    print("\nAgent:", agent.name)
    print("Response:", result)

    assert agent.name == "Test Agent"
    assert isinstance(result, str)

    print("\n" + "=" * 60)
    print("BASE AGENT TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
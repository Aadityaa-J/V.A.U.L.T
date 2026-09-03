from tools.adapters import CalculateTool
from tools.registry import ToolRegistry


def main():
    print("=" * 60)
    print("CALCULATE TOOL INTEGRATION TEST")
    print("=" * 60)

    calculator = CalculateTool()

    result = calculator.execute(
        "(10 + 5) * 2"
    )

    print("\nDIRECT TOOL RESULT:")
    print(result)

    assert result == 30

    registry = ToolRegistry()

    registry.register(calculator)

    assert registry.has("calculate")

    registered_tool = registry.get("calculate")

    registry_result = registered_tool.execute(
        "100 / 4"
    )

    print("\nREGISTRY TOOL RESULT:")
    print(registry_result)

    assert registry_result == 25

    print("\n" + "=" * 60)
    print("CALCULATE TOOL INTEGRATION TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
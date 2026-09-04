from tools.adapters import RunPythonTool
from tools.registry import ToolRegistry


def main():
    print("=" * 60)
    print("SANDBOX TOOL INTEGRATION TEST")
    print("=" * 60)

    sandbox = RunPythonTool()

    code = """
print("Hello from V.A.U.L.T.")
result = 10 + 20
print(result)
"""

    result = sandbox.execute(code)

    print("\nDIRECT TOOL RESULT:")
    print(result)

    assert result["success"] is True
    assert "Hello from V.A.U.L.T." in result["stdout"]
    assert "30" in result["stdout"]
    assert result["return_code"] == 0

    registry = ToolRegistry()

    registry.register(sandbox)

    assert registry.has("run_python")

    registered_tool = registry.get("run_python")

    registry_result = registered_tool.execute(
        'print("Registry execution works")'
    )

    print("\nREGISTRY TOOL RESULT:")
    print(registry_result)

    assert registry_result["success"] is True

    assert (
        "Registry execution works"
        in registry_result["stdout"]
    )

    print("\n" + "=" * 60)
    print("SANDBOX TOOL INTEGRATION TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
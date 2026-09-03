from tools.base import BaseTool
from tools.registry import ToolRegistry


class TestTool(BaseTool):
    name = "test_tool"
    description = "A tool used for testing."

    def execute(self, arguments):
        return f"Executed with: {arguments}"


registry = ToolRegistry()

tool = TestTool()

registry.register(tool)

print("\n" + "=" * 60)
print("TOOL REGISTRY TEST")
print("=" * 60)

print("Has test_tool:", registry.has("test_tool"))

retrieved_tool = registry.get("test_tool")

print("Tool name:", retrieved_tool.name)
print("Tool description:", retrieved_tool.description)
print(
    "Execution result:",
    retrieved_tool.execute("hello")
)

print("Registered tools:", list(registry.get_all().keys()))

try:
    registry.register(TestTool())
except ValueError as exc:
    print("Duplicate protection:", exc)
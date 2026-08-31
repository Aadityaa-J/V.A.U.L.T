from agents.base import BaseAgent


agent = BaseAgent(
    name="Test Agent",
    task_type="simple"
)

result = agent.run("Say hello and identify yourself as a test agent.")

print("\nAgent:", agent.name)
print("Response:", result)
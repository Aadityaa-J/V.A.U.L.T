from agents.coding_agent import CodingAgent


agent = CodingAgent()

task = """
Write a Python function called calculate_efficiency
that accepts useful_output and total_input and returns
the efficiency as a percentage.
"""

result = agent.run(task)

print("\n" + "=" * 60)
print("CODING AGENT TEST")
print("=" * 60)
print(result)
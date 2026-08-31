from agents.engineering_agent import EngineeringAgent


agent = EngineeringAgent()

task = """
A pump consumes 10 kW of input power and delivers
8 kW of useful hydraulic power.

Calculate the pump efficiency as a percentage.
Show the formula, substitution, intermediate calculation,
and final result.
"""

result = agent.run(task)

print("\n" + "=" * 60)
print("ENGINEERING AGENT TEST")
print("=" * 60)
print(result)
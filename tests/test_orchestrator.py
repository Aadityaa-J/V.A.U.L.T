from agents.orchestrator import Orchestrator


orchestrator = Orchestrator()

task = """
A pump consumes 10 kW of input power and produces
8 kW of useful hydraulic power.

Calculate its efficiency and show the formula and
calculation steps.
"""

result = orchestrator.run(
    task=task,
    task_type="engineering"
)

print("\n" + "=" * 60)
print("ORCHESTRATOR TEST")
print("=" * 60)
print(result)
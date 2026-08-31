from agents.document_agent import DocumentAgent


agent = DocumentAgent()

task = """
Analyze the following fictional inspection information:

Equipment: Pump P-204
Inspection date: August 2026
Vibration: 4.2 mm/s
Temperature: 78 C
Observation: Increased vibration compared with previous inspection.

Identify the important findings and any uncertainties.
"""

result = agent.run(task)

print("\n" + "=" * 60)
print("DOCUMENT AGENT TEST")
print("=" * 60)
print(result)
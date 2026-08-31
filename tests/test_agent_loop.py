from agents.agent_loop import AgentLoop


def calculator(arguments: str):
    return "The calculation result is 80%."


loop = AgentLoop(
    system_prompt="""
You are a simple engineering assistant.
Use the calculator when a calculation is required.
""",
    tools={
        "calculator": calculator
    },
    max_steps=3
)

result = loop.run(
    """
Calculate the efficiency of a pump that produces
8 kW of useful output from 10 kW of input.
"""
)

print("\n" + "=" * 60)
print("AGENT LOOP TEST")
print("=" * 60)
print(result)
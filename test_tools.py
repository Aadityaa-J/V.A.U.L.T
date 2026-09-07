from tools.adapters import (
    CalculateTool,
    RunPythonTool,
)


def main():

    print()
    print("=" * 60)
    print("V.A.U.L.T. TOOL TEST")
    print("=" * 60)

    # ==================================================
    # CALCULATOR TEST
    # ==================================================

    print()
    print("CALCULATOR TEST")
    print("-" * 60)

    calculator = CalculateTool()

    try:

        result = calculator.execute(
            "25 * 48"
        )

        print("Expression: 25 * 48")
        print("Result:", result)

    except Exception as error:

        print("ERROR:", error)

    # ==================================================
    # PYTHON TEST
    # ==================================================

    print()
    print("PYTHON TOOL TEST")
    print("-" * 60)

    python_tool = RunPythonTool()

    code = """
result = 0

for number in range(1, 11):
    result += number

print(result)
"""

    try:

        result = python_tool.execute(
            code
        )

        print("Python Code:")
        print(code)

        print("Execution Result:")
        print(result)

    except Exception as error:

        print("ERROR:", error)

    print()
    print("=" * 60)
    print("TOOL TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
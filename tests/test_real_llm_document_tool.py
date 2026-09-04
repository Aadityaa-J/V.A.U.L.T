from pathlib import Path
import tempfile

from agents.orchestrator import Orchestrator


def main():
    print("=" * 60)
    print("REAL LLM DOCUMENT TOOL SELECTION TEST")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:

        document_path = (
            Path(temp_dir) / "inspection_report.txt"
        )

        document_path.write_text(
            """
Pump Inspection Report

During the inspection, the pump temperature reached
95 degrees Celsius.

The recommended operating temperature is below
80 degrees Celsius.

Pressure remained stable throughout the test.

The inspection team recommends maintenance because
the pump temperature exceeded the normal operating
range.
""".strip(),
            encoding="utf-8",
        )

        print("\nDOCUMENT CREATED:")
        print(document_path)

        orchestrator = Orchestrator()

        task = f"""
Read and analyze the inspection report located at:

{document_path}

Use the available document tools to inspect the file.

Provide a concise summary of the findings.
Do not claim to have read the document unless you
actually use a document tool.
"""

        print("\nTASK:")
        print(task)

        print("\nRunning real agent...\n")

        result = orchestrator.run(task)

        print("=" * 60)
        print("FINAL RESULT")
        print("=" * 60)

        print(result)

        print("\n" + "=" * 60)
        print("TEST COMPLETED")
        print("=" * 60)


if __name__ == "__main__":
    main()
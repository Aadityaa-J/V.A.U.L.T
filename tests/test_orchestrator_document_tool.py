from pathlib import Path
import tempfile

from agents.orchestrator import Orchestrator


def fake_generate(prompt: str, model: str) -> str:
    """
    First call reads the document.
    Second call returns a final answer based on
    the tool observation.
    """

    fake_generate.calls += 1

    if fake_generate.calls == 1:
        return f"""
ACTION: tool
NAME: read_document
ARGUMENTS: {fake_generate.document_path}
"""

    return """
ACTION: final
CONTENT: The document was read successfully. It reports that the pump temperature was higher than expected and maintenance is recommended.
"""


fake_generate.calls = 0
fake_generate.document_path = ""


def main():
    print("=" * 60)
    print("FULL ORCHESTRATOR + DOCUMENT TOOL TEST")
    print("=" * 60)

    import agents.agent_loop as agent_loop_module
    import agents.task_classifier as classifier_module

    original_generate = agent_loop_module.generate
    original_classify = (
        classifier_module.TaskClassifier.classify
    )

    try:
        with tempfile.TemporaryDirectory() as temp_dir:

            document_path = (
                Path(temp_dir) / "inspection_report.txt"
            )

            document_path.write_text(
                """
Pump Inspection Report

The pump temperature was higher than expected.

Pressure remained stable during testing.

Maintenance is recommended because the pump
temperature exceeded the normal operating range.
""".strip(),
                encoding="utf-8",
            )

            fake_generate.document_path = str(
                document_path
            )

            # Mock the LLM.
            agent_loop_module.generate = fake_generate

            # Force routing to Document Agent.
            def fake_classify(self, task):
                return "document"

            classifier_module.TaskClassifier.classify = (
                fake_classify
            )

            orchestrator = Orchestrator()

            result = orchestrator.run(
                "Read the inspection report and summarize it."
            )

            print("\nFINAL RESULT:")
            print(result)

            print("\nLLM CALLS:")
            print(fake_generate.calls)

            assert (
                "maintenance is recommended"
                in result.lower()
            )

            assert fake_generate.calls == 2

            document_tools = (
                orchestrator._get_agent_tools(
                    "document"
                )
            )

            print("\nDOCUMENT AGENT TOOLS:")
            print(list(document_tools.keys()))

            assert "read_document" in document_tools

            print("\n" + "=" * 60)
            print(
                "FULL ORCHESTRATOR + DOCUMENT TOOL TEST PASSED"
            )
            print("=" * 60)

    finally:
        agent_loop_module.generate = original_generate

        classifier_module.TaskClassifier.classify = (
            original_classify
        )


if __name__ == "__main__":
    main()
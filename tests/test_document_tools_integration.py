from pathlib import Path
import tempfile
import json

from tools.adapters import (
    ReadDocumentTool,
    DocumentInfoTool,
    SearchDocumentTool,
    DocumentSummaryTool,
)
from tools.registry import ToolRegistry


def main():
    print("=" * 60)
    print("DOCUMENT TOOLS INTEGRATION TEST")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        document = root / "report.txt"

        document.write_text(
            """
Pump inspection report.

The pump temperature was higher than expected.

Pressure remained stable during testing.

Maintenance is recommended because the pump
temperature exceeded the normal operating range.
""".strip(),
            encoding="utf-8",
        )

        read_tool = ReadDocumentTool()
        info_tool = DocumentInfoTool()
        search_tool = SearchDocumentTool()
        summary_tool = DocumentSummaryTool()

        # --------------------------------------------------
        # READ DOCUMENT
        # --------------------------------------------------

        content = read_tool.execute(str(document))

        print("\nDOCUMENT CONTENT:")
        print(content)

        assert "Pump inspection report" in content

        # --------------------------------------------------
        # DOCUMENT INFO
        # --------------------------------------------------

        info = info_tool.execute(str(document))

        print("\nDOCUMENT INFO:")
        print(info)

        assert info["name"] == "report.txt"
        assert info["lines"] > 0
        assert info["words"] > 0

        # --------------------------------------------------
        # SEARCH DOCUMENT
        # --------------------------------------------------

        search_arguments = json.dumps({
            "file_path": str(document),
            "query": "temperature",
        })

        matches = search_tool.execute(
            search_arguments
        )

        print("\nSEARCH RESULTS:")
        print(matches)

        assert len(matches) >= 2

        # --------------------------------------------------
        # DOCUMENT SUMMARY
        # --------------------------------------------------

        summary_arguments = json.dumps({
            "file_path": str(document),
            "max_words": 15,
        })

        summary = summary_tool.execute(
            summary_arguments
        )

        print("\nDOCUMENT SUMMARY:")
        print(summary)

        assert isinstance(summary, str)
        assert len(summary) > 0

        # --------------------------------------------------
        # REGISTRY
        # --------------------------------------------------

        registry = ToolRegistry()

        tools = [
            read_tool,
            info_tool,
            search_tool,
            summary_tool,
        ]

        for tool in tools:
            registry.register(tool)

        assert registry.has("read_document")
        assert registry.has("document_info")
        assert registry.has("search_document")
        assert registry.has("document_summary")

        print("\nREGISTERED DOCUMENT TOOLS:")
        print(list(registry.get_all().keys()))

    print("\n" + "=" * 60)
    print("DOCUMENT TOOLS INTEGRATION TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
from pathlib import Path
import tempfile
import json

from tools.adapters import (
    ListFilesTool,
    ListDirectoryTool,
    FileExistsTool,
    CreateDirectoryTool,
    CopyFileTool,
    MoveFileTool,
)
from tools.registry import ToolRegistry


def main():
    print("=" * 60)
    print("FILE TOOLS INTEGRATION TEST")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        source_file = root / "source.txt"
        source_file.write_text(
            "Hello from V.A.U.L.T.",
            encoding="utf-8",
        )

        list_files_tool = ListFilesTool()
        list_directory_tool = ListDirectoryTool()
        file_exists_tool = FileExistsTool()
        create_directory_tool = CreateDirectoryTool()
        copy_file_tool = CopyFileTool()
        move_file_tool = MoveFileTool()

        # --------------------------------------------------
        # LIST FILES
        # --------------------------------------------------

        files = list_files_tool.execute(str(root))

        print("\nFILES:")
        print(files)

        assert str(source_file) in files

        # --------------------------------------------------
        # LIST DIRECTORY
        # --------------------------------------------------

        directory_items = list_directory_tool.execute(
            str(root)
        )

        print("\nDIRECTORY ITEMS:")
        print(directory_items)

        assert len(directory_items) >= 1

        # --------------------------------------------------
        # FILE EXISTS
        # --------------------------------------------------

        exists = file_exists_tool.execute(
            str(source_file)
        )

        print("\nFILE EXISTS:")
        print(exists)

        assert exists is True

        # --------------------------------------------------
        # CREATE DIRECTORY
        # --------------------------------------------------

        new_directory = root / "created"

        created_path = create_directory_tool.execute(
            str(new_directory)
        )

        print("\nCREATED DIRECTORY:")
        print(created_path)

        assert new_directory.exists()
        assert new_directory.is_dir()

        # --------------------------------------------------
        # COPY FILE
        # --------------------------------------------------

        copied_file = new_directory / "copied.txt"

        copy_arguments = json.dumps({
            "source": str(source_file),
            "destination": str(copied_file),
        })

        copy_result = copy_file_tool.execute(
            copy_arguments
        )

        print("\nCOPIED FILE:")
        print(copy_result)

        assert copied_file.exists()

        # --------------------------------------------------
        # MOVE FILE
        # --------------------------------------------------

        moved_file = root / "moved.txt"

        move_arguments = json.dumps({
            "source": str(copied_file),
            "destination": str(moved_file),
        })

        move_result = move_file_tool.execute(
            move_arguments
        )

        print("\nMOVED FILE:")
        print(move_result)

        assert moved_file.exists()
        assert not copied_file.exists()

        # --------------------------------------------------
        # REGISTRY
        # --------------------------------------------------

        registry = ToolRegistry()

        tools = [
            list_files_tool,
            list_directory_tool,
            file_exists_tool,
            create_directory_tool,
            copy_file_tool,
            move_file_tool,
        ]

        for tool in tools:
            registry.register(tool)

        assert registry.has("list_files")
        assert registry.has("list_directory")
        assert registry.has("file_exists")
        assert registry.has("create_directory")
        assert registry.has("copy_file")
        assert registry.has("move_file")

        print("\nREGISTERED FILE TOOLS:")
        print(list(registry.get_all().keys()))

    print("\n" + "=" * 60)
    print("FILE TOOLS INTEGRATION TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
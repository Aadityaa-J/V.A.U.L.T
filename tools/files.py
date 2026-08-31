"""
File-system tools for V.A.U.L.T.
"""

from pathlib import Path
import shutil


def list_files(directory: str = ".") -> list[str]:
    """
    List files in a directory.
    """

    path = Path(directory)

    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not path.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    return [
        str(item)
        for item in path.iterdir()
        if item.is_file()
    ]


def list_directory(directory: str = ".") -> list[dict]:
    """
    List files and directories with basic metadata.
    """

    path = Path(directory)

    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not path.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    results = []

    for item in path.iterdir():
        results.append({
            "name": item.name,
            "path": str(item),
            "type": "directory" if item.is_dir() else "file",
            "size_bytes": item.stat().st_size if item.is_file() else None,
        })

    return results


def file_exists(file_path: str) -> bool:
    """Check whether a file exists."""

    return Path(file_path).is_file()


def directory_exists(directory: str) -> bool:
    """Check whether a directory exists."""

    return Path(directory).is_dir()


def create_directory(directory: str) -> str:
    """Create a directory if it does not already exist."""

    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)

    return str(path.absolute())


def delete_file(file_path: str) -> bool:
    """Delete a file."""

    path = Path(file_path)

    if not path.exists():
        return False

    if not path.is_file():
        raise ValueError(f"Not a file: {file_path}")

    path.unlink()

    return True


def copy_file(source: str, destination: str) -> str:
    """Copy a file to a destination."""

    source_path = Path(source)
    destination_path = Path(destination)

    if not source_path.is_file():
        raise FileNotFoundError(f"Source file not found: {source}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(source_path, destination_path)

    return str(destination_path.absolute())


def move_file(source: str, destination: str) -> str:
    """Move a file to a destination."""

    source_path = Path(source)
    destination_path = Path(destination)

    if not source_path.exists():
        raise FileNotFoundError(f"Source not found: {source}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)

    shutil.move(str(source_path), str(destination_path))

    return str(destination_path.absolute())
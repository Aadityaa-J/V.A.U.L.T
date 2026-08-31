"""
Sandbox execution tools for V.A.U.L.T.

Provides controlled execution of Python code without exposing
arbitrary shell commands directly to the agent.
"""

import subprocess
import sys
import tempfile
from pathlib import Path


DEFAULT_TIMEOUT = 10
MAX_OUTPUT_LENGTH = 10000


def run_python(
    code: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """
    Execute Python code inside a temporary file.

    Returns:
        {
            "success": bool,
            "stdout": str,
            "stderr": str,
            "return_code": int
        }
    """

    if not isinstance(code, str):
        raise TypeError("Code must be a string.")

    if not code.strip():
        raise ValueError("Code cannot be empty.")

    if timeout <= 0:
        raise ValueError("Timeout must be greater than zero.")

    if timeout > 60:
        timeout = 60

    temp_file = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as file:
            file.write(code)
            temp_file = Path(file.name)

        process = subprocess.run(
            [sys.executable, str(temp_file)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        stdout = process.stdout[:MAX_OUTPUT_LENGTH]
        stderr = process.stderr[:MAX_OUTPUT_LENGTH]

        return {
            "success": process.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": process.returncode,
        }

    except subprocess.TimeoutExpired as exc:
        return {
            "success": False,
            "stdout": (exc.stdout or "")[:MAX_OUTPUT_LENGTH],
            "stderr": "Execution timed out.",
            "return_code": -1,
        }

    finally:
        if temp_file and temp_file.exists():
            temp_file.unlink()


def validate_python(code: str) -> dict:
    """
    Check whether Python code is syntactically valid
    without executing it.
    """

    import ast

    try:
        ast.parse(code)

        return {
            "valid": True,
            "error": None,
        }

    except SyntaxError as exc:
        return {
            "valid": False,
            "error": {
                "message": exc.msg,
                "line": exc.lineno,
                "column": exc.offset,
            },
        }
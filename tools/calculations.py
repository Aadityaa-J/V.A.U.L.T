"""
Calculation tools for V.A.U.L.T.
"""

import ast
import math
import operator


# Supported binary operators
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.FloorDiv: operator.floordiv,
}

# Supported unary operators
_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def calculate(expression: str) -> float:
    """
    Safely evaluate a mathematical expression.

    Examples:
        calculate("10 + 5")
        calculate("2 ** 8")
        calculate("(10 + 5) * 2")
    """

    if not isinstance(expression, str):
        raise TypeError("Expression must be a string.")

    expression = expression.strip()

    if not expression:
        raise ValueError("Expression cannot be empty.")

    try:
        tree = ast.parse(expression, mode="eval")
        result = _evaluate(tree.body)
    except ZeroDivisionError:
        raise ValueError("Cannot divide by zero.")
    except Exception as exc:
        raise ValueError(f"Invalid mathematical expression: {expression}") from exc

    return result


def _evaluate(node):
    """Recursively evaluate an AST node."""

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("Only numeric values are allowed.")

    if isinstance(node, ast.BinOp):
        operation = _OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError("Unsupported mathematical operator.")

        left = _evaluate(node.left)
        right = _evaluate(node.right)

        return operation(left, right)

    if isinstance(node, ast.UnaryOp):
        operation = _UNARY_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError("Unsupported unary operator.")

        return operation(_evaluate(node.operand))

    raise ValueError("Unsupported expression.")


def percentage(value: float, percent: float) -> float:
    """Calculate a percentage of a value."""

    return value * (percent / 100)


def average(numbers: list[float]) -> float:
    """Calculate the arithmetic mean."""

    if not numbers:
        raise ValueError("Cannot calculate average of an empty list.")

    return sum(numbers) / len(numbers)


def round_number(value: float, digits: int = 2) -> float:
    """Round a number to a specified number of decimal places."""

    return round(value, digits)
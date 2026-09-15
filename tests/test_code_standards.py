"""Checks the standards that ruff and mypy do not enforce: function length, nesting, docstrings."""

import ast
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parent.parent
PACKAGE_DIR = PROJECT_DIR / "faultline_noc"
SCRIPTS_DIR = PROJECT_DIR / "scripts"
MAX_FUNCTION_LINES = 30
MAX_NESTING_DEPTH = 3
FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
NESTING_NODES = (
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.If,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.Match,
)
PENDING_WORK_MARKER = "TO" + "DO"
SOURCE_FILES = sorted([*PACKAGE_DIR.rglob("*.py"), *SCRIPTS_DIR.rglob("*.py")])


def _functions(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return every function and method defined in a source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [node for node in ast.walk(tree) if isinstance(node, FUNCTION_NODES)]


def _nesting_depth(node: ast.AST, depth: int = 0) -> int:
    """Return the deepest block nesting under a node, counting an elif as the same level."""
    deepest = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, FUNCTION_NODES):
            continue
        is_elif = isinstance(node, ast.If) and node.orelse == [child]
        steps = isinstance(child, NESTING_NODES) and not is_elif
        deepest = max(deepest, _nesting_depth(child, depth + int(steps)))
    return deepest


@pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda path: path.name)
def test_functions_are_short_documented_and_shallow(path: Path) -> None:
    """Every function has a docstring, at most 30 lines and nesting depth of at most 3."""
    for function in _functions(path):
        label = f"{path.name}:{function.lineno} {function.name}"
        length = (function.end_lineno or function.lineno) - function.lineno + 1
        assert ast.get_docstring(function), f"{label} has no docstring"
        assert length <= MAX_FUNCTION_LINES, f"{label} is {length} lines"
        assert _nesting_depth(function) <= MAX_NESTING_DEPTH, f"{label} nests too deeply"


def test_no_pending_work_markers_in_the_repo() -> None:
    """No source or test file carries a pending-work marker."""
    files = [*SOURCE_FILES, *sorted((PROJECT_DIR / "tests").rglob("*.py"))]
    offenders = [
        path.name for path in files if PENDING_WORK_MARKER in path.read_text(encoding="utf-8")
    ]
    assert offenders == []

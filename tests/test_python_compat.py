from __future__ import annotations

import ast
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def test_source_syntax_is_python_311_compatible() -> None:
    for path in sorted((REPO / "src").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path), feature_version=(3, 11))

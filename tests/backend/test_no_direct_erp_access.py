from __future__ import annotations

from pathlib import Path


def test_no_backend_module_opens_direct_erp_connection_outside_readonly_boundary() -> None:
    backend_root = Path("src/backend/chatbot_rpinfo")
    forbidden_snippets = (
        "import psycopg",
        "from psycopg",
        "import psycopg2",
        "from psycopg2",
        "import pyodbc",
        "from pyodbc",
        "import asyncpg",
        "from asyncpg",
        "import sqlalchemy",
        "from sqlalchemy",
    )

    offenders: list[str] = []
    for path in backend_root.rglob("*.py"):
        relative_parts = path.relative_to(backend_root).parts
        if relative_parts[0] == "erp_readonly":
            continue
        text = path.read_text(encoding="utf-8")
        for snippet in forbidden_snippets:
            if snippet in text:
                offenders.append(f"{path}:{snippet}")

    assert offenders == []

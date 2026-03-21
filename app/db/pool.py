from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import psycopg

from app.config import get_settings
def get_connection() -> psycopg.Connection[Any]:
    # autocommit=False means transactions require explicit commit/rollback, ensuring atomicity and control; autocommit=True commits each statement immediately, which risks partial writes and inconsistent states if errors occur.
    settings = get_settings()
    conn = psycopg.connect(settings.database)  # Establish connection to postgresdb
    conn.autocommit = False
    return conn

# Enables 'with' usage for DB connection; auto-closes connection safely.
@contextmanager
def connection_context() -> Generator[psycopg.Connection[Any], None, None]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()

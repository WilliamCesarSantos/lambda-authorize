"""Role repository — reserved for future role-related queries.

Currently, roles are returned directly by user_repository.
This module provides a placeholder for more advanced role queries.
"""

from __future__ import annotations

import psycopg


def list_roles_for_user(conn: psycopg.Connection, user_id: str) -> list[str]:
    """Return the list of roles for a given user_id."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT roles FROM users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()

    if row is None or not row[0]:
        return []

    return list(row[0])

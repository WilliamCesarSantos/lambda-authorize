"""User repository — queries the users table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import psycopg


@dataclass
class User:
    id: str
    name: str
    email: str
    password_hash: str
    roles: list[str]


def find_by_email(conn: psycopg.Connection, email: str) -> Optional[User]:
    """Return a User for the given email, or None if not found."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, email, password_hash, roles FROM users WHERE email = %s",
            (email,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return User(
        id=str(row[0]),
        name=row[1],
        email=row[2],
        password_hash=row[3],
        roles=list(row[4]) if row[4] else [],
    )

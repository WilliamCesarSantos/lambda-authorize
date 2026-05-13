"""Unit tests for role_repository."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from unittest.mock import MagicMock
from repositories.role_repository import list_roles_for_user


def _make_conn(row):
    cur = MagicMock()
    cur.fetchone.return_value = row
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn


def test_list_roles_found():
    conn = _make_conn((["admin", "read"],))
    roles = list_roles_for_user(conn, "abc-123")
    assert roles == ["admin", "read"]


def test_list_roles_empty():
    conn = _make_conn(([], ))
    roles = list_roles_for_user(conn, "abc-123")
    assert roles == []


def test_list_roles_user_not_found():
    conn = _make_conn(None)
    roles = list_roles_for_user(conn, "nonexistent")
    assert roles == []

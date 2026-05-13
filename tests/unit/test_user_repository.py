"""Unit tests for user_repository."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

import pytest
from unittest.mock import MagicMock
from repositories.user_repository import find_by_email, User


def _make_conn(row):
    cur = MagicMock()
    cur.fetchone.return_value = row
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn


def test_find_by_email_found():
    row = ("abc-123", "Test User", "test@example.com", "hashed_pw", ["admin"])
    conn = _make_conn(row)

    user = find_by_email(conn, "test@example.com")

    assert user is not None
    assert user.id == "abc-123"
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.password_hash == "hashed_pw"
    assert user.roles == ["admin"]


def test_find_by_email_not_found():
    conn = _make_conn(None)
    user = find_by_email(conn, "notfound@example.com")
    assert user is None


def test_find_by_email_empty_roles():
    row = ("xyz", "No Roles", "noroles@example.com", "hash", [])
    conn = _make_conn(row)

    user = find_by_email(conn, "noroles@example.com")
    assert user.roles == []

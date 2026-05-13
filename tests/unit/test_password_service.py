"""Unit tests for password_service."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from argon2 import PasswordHasher
from services.password_service import verify

_ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)
PEPPER = "test-pepper"


def _make_hash(password: str) -> str:
    return _ph.hash(password + PEPPER)


def test_verify_correct_password():
    stored = _make_hash("correct_password")
    assert verify("correct_password", stored, PEPPER) is True


def test_verify_wrong_password():
    stored = _make_hash("correct_password")
    assert verify("wrong_password", stored, PEPPER) is False


def test_verify_wrong_pepper():
    stored = _make_hash("correct_password")
    assert verify("correct_password", stored, "wrong-pepper") is False


def test_verify_invalid_hash():
    assert verify("any_password", "not_a_valid_hash", PEPPER) is False

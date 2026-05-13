"""Password hashing and verification using Argon2id with pepper."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

_ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)


def verify(password: str, stored_hash: str, pepper: str) -> bool:
    """Return True if password+pepper matches the stored Argon2id hash."""
    try:
        return _ph.verify(stored_hash, password + pepper)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False

"""JWT token issuance service (RS256)."""

import os
from datetime import datetime, timedelta, timezone

import jwt

from services import secrets_service


def issue(user: dict) -> str:
    """Issue a signed RS256 JWT for the given user dict.

    The user dict must contain: id, name, email, roles.
    """
    private_key = secrets_service.get_private_key()
    expiration_hours = int(os.environ.get("JWT_EXPIRATION_HOURS", "1"))
    kid = os.environ.get("JWKS_KID", "dev-key-1")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "name": user["name"],
        "email": user["email"],
        "roles": user.get("roles") or [],
        "iat": now,
        "exp": now + timedelta(hours=expiration_hours),
    }

    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})

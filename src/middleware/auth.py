"""JWT authentication middleware."""

import json

import jwt

from services import secrets_service


def _build_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def require_jwt(event: dict, next_handler):
    """Verify the Bearer JWT in the Authorization header.

    Calls next_handler(event) if the token is valid.
    Returns 401 if the token is missing, invalid, or expired.
    """
    auth_header: str = (
        (event.get("headers") or {}).get("Authorization")
        or (event.get("headers") or {}).get("authorization")
        or ""
    )

    if not auth_header.startswith("Bearer "):
        return _build_response(401, {"error": "Token de autorização ausente ou inválido"})

    token = auth_header[len("Bearer "):]

    try:
        public_key = secrets_service.get_public_key()
        jwt.decode(token, public_key, algorithms=["RS256"])
    except jwt.ExpiredSignatureError:
        return _build_response(401, {"error": "Token expirado"})
    except jwt.InvalidTokenError:
        return _build_response(401, {"error": "Token inválido"})

    return next_handler(event)

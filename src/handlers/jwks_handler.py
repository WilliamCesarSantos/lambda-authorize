"""JWKS handler — GET /.well-known/jwks.json (requires Bearer token)."""

import json

from botocore.exceptions import BotoCoreError, ClientError

from services import secrets_service, jwks_service


def _build_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def handle(event: dict) -> dict:
    """Return the JWKS for the current RSA public key."""
    try:
        public_key_pem = secrets_service.get_public_key()
    except (BotoCoreError, ClientError) as exc:
        return _build_response(500, {"error": f"Erro ao buscar chave pública: {exc}"})

    jwks = jwks_service.build_jwks(public_key_pem)
    return _build_response(200, jwks)

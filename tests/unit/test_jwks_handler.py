"""Unit tests for jwks_handler."""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))


def _event_with_token(token: str) -> dict:
    return {
        "rawPath": "/.well-known/jwks.json",
        "requestContext": {"http": {"method": "GET"}},
        "headers": {"Authorization": f"Bearer {token}"},
    }


def test_jwks_no_token(mocker):
    from middleware.auth import require_jwt
    from handlers import jwks_handler

    event = {"rawPath": "/.well-known/jwks.json", "headers": {}}
    resp = require_jwt(event, jwks_handler.handle)
    assert resp["statusCode"] == 401


def test_jwks_invalid_token(mocker, rsa_key_pair):
    mocker.patch("middleware.auth.secrets_service.get_public_key", return_value=rsa_key_pair["public_pem"])

    from middleware.auth import require_jwt
    from handlers import jwks_handler

    resp = require_jwt(_event_with_token("invalid.token.here"), jwks_handler.handle)
    assert resp["statusCode"] == 401


def test_jwks_valid_token_returns_jwks(mocker, rsa_key_pair):
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone

    token = pyjwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        rsa_key_pair["private_pem"],
        algorithm="RS256",
    )
    mocker.patch("middleware.auth.secrets_service.get_public_key", return_value=rsa_key_pair["public_pem"])
    mocker.patch("handlers.jwks_handler.secrets_service.get_public_key", return_value=rsa_key_pair["public_pem"])
    mocker.patch.dict(os.environ, {"JWKS_KID": "test-kid"})

    from middleware.auth import require_jwt
    from handlers import jwks_handler

    resp = require_jwt(_event_with_token(token), jwks_handler.handle)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "keys" in body
    assert len(body["keys"]) == 1
    key = body["keys"][0]
    assert key["kty"] == "RSA"
    assert key["alg"] == "RS256"
    assert "n" in key
    assert "e" in key

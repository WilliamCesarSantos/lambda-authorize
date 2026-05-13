"""Unit tests for token_service."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

import jwt
import pytest


def test_issue_returns_valid_jwt(mocker, rsa_key_pair):
    mocker.patch("services.secrets_service.get_private_key", return_value=rsa_key_pair["private_pem"])
    mocker.patch.dict(os.environ, {"JWT_EXPIRATION_HOURS": "1", "JWKS_KID": "test-kid"})

    from services import token_service

    user = {
        "id": "abc-123",
        "name": "Test User",
        "email": "test@example.com",
        "roles": ["admin"],
    }
    token = token_service.issue(user)

    decoded = jwt.decode(token, rsa_key_pair["public_pem"], algorithms=["RS256"])
    assert decoded["sub"] == "abc-123"
    assert decoded["name"] == "Test User"
    assert decoded["email"] == "test@example.com"
    assert decoded["roles"] == ["admin"]


def test_issue_includes_kid_in_header(mocker, rsa_key_pair):
    mocker.patch("services.secrets_service.get_private_key", return_value=rsa_key_pair["private_pem"])
    mocker.patch.dict(os.environ, {"JWKS_KID": "my-key-id"})

    from services import token_service

    user = {"id": "1", "name": "X", "email": "x@x.com", "roles": []}
    token = token_service.issue(user)

    header = jwt.get_unverified_header(token)
    assert header["kid"] == "my-key-id"
    assert header["alg"] == "RS256"


def test_issue_empty_roles(mocker, rsa_key_pair):
    mocker.patch("services.secrets_service.get_private_key", return_value=rsa_key_pair["private_pem"])
    mocker.patch.dict(os.environ, {"JWKS_KID": "k"})

    from services import token_service

    user = {"id": "2", "name": "Y", "email": "y@y.com", "roles": []}
    token = token_service.issue(user)

    decoded = jwt.decode(token, rsa_key_pair["public_pem"], algorithms=["RS256"])
    assert decoded["roles"] == []

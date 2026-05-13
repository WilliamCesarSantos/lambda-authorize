"""Unit tests for login_handler."""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))


def _event(body):
    return {
        "rawPath": "/login",
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps(body) if isinstance(body, dict) else body,
    }


def test_login_missing_fields(mocker):
    from handlers import login_handler

    resp = login_handler.handle(_event({"email": "a@a.com"}))
    assert resp["statusCode"] == 400


def test_login_invalid_json(mocker):
    from handlers import login_handler

    resp = login_handler.handle({"rawPath": "/login", "body": "not-json"})
    assert resp["statusCode"] == 400


def test_login_user_not_found(mocker):
    mocker.patch("handlers.login_handler.get_connection")
    mocker.patch("handlers.login_handler.user_repository.find_by_email", return_value=None)

    from handlers import login_handler

    resp = login_handler.handle(_event({"email": "x@x.com", "password": "pass"}))
    assert resp["statusCode"] == 401


def test_login_wrong_password(mocker):
    from repositories.user_repository import User

    mock_user = User(
        id="abc",
        name="Test",
        email="test@example.com",
        password_hash="$argon2id$...",
        roles=[],
    )
    mocker.patch("handlers.login_handler.get_connection")
    mocker.patch("handlers.login_handler.user_repository.find_by_email", return_value=mock_user)
    mocker.patch("handlers.login_handler.secrets_service.get_pepper", return_value="pepper")
    mocker.patch("handlers.login_handler.password_service.verify", return_value=False)

    from handlers import login_handler

    resp = login_handler.handle(_event({"email": "test@example.com", "password": "wrong"}))
    assert resp["statusCode"] == 401


def test_login_success(mocker, rsa_key_pair):
    from repositories.user_repository import User

    mock_user = User(
        id="abc-123",
        name="Test",
        email="test@example.com",
        password_hash="valid_hash",
        roles=["admin"],
    )
    mocker.patch("handlers.login_handler.get_connection")
    mocker.patch("handlers.login_handler.user_repository.find_by_email", return_value=mock_user)
    mocker.patch("handlers.login_handler.secrets_service.get_pepper", return_value="pepper")
    mocker.patch("handlers.login_handler.password_service.verify", return_value=True)
    mocker.patch("handlers.login_handler.token_service.issue", return_value="signed.jwt.token")

    from handlers import login_handler

    resp = login_handler.handle(_event({"email": "test@example.com", "password": "correct"}))
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["token"] == "signed.jwt.token"

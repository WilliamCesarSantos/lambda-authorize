"""Shared fixtures for unit tests."""

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


@pytest.fixture(scope="session")
def rsa_key_pair():
    """Generate an RSA key pair for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return {"private_pem": private_pem, "public_pem": public_pem}


@pytest.fixture
def mock_user():
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Test User",
        "email": "test@example.com",
        "password_hash": "dummy_hash",
        "roles": ["admin"],
    }


@pytest.fixture
def mock_event_login():
    return {
        "rawPath": "/login",
        "requestContext": {"http": {"method": "POST"}},
        "body": '{"email": "test@example.com", "password": "secret"}',
    }

"""JWKS builder — converts an RSA public key PEM to JWKS format (RFC 7517)."""

import base64
import os

from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey


def _b64url(n: int) -> str:
    """Encode a large integer as base64url without padding."""
    byte_length = (n.bit_length() + 7) // 8
    b = n.to_bytes(byte_length, byteorder="big")
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def build_jwks(public_key_pem: str) -> dict:
    """Return a JWKS dict for the given RSA public key PEM."""
    key: RSAPublicKey = load_pem_public_key(public_key_pem.encode("utf-8"))  # type: ignore[assignment]
    pub_numbers = key.public_numbers()

    kid = os.environ.get("JWKS_KID", "dev-key-1")

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": kid,
                "n": _b64url(pub_numbers.n),
                "e": _b64url(pub_numbers.e),
            }
        ]
    }

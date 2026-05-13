"""
Lambda Authorizer — emite tokens JWT RS256 e expõe chave pública em formato JWKS.

Endpoints:
  POST /login                   — autentica e retorna um JWT assinado com chave privada RSA
  GET  /.well-known/jwks.json   — retorna a chave pública no formato JWKS (requer Bearer token)
"""

import json

from handlers import login_handler, jwks_handler
from middleware.auth import require_jwt


def _build_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _get_http_method(event: dict) -> str:
    return (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
        or "POST"
    ).upper()


def _get_path(event: dict) -> str:
    return event.get("path") or event.get("rawPath") or "/"


def lambda_handler(event: dict, context) -> dict:  # noqa: ANN001
    method = _get_http_method(event)
    path = _get_path(event)

    if method == "POST" and path.rstrip("/") == "/login":
        return login_handler.handle(event)

    if method == "GET" and path.rstrip("/") == "/.well-known/jwks.json":
        return require_jwt(event, jwks_handler.handle)

    return _build_response(404, {"error": "Rota não encontrada"})

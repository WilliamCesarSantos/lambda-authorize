"""
Lambda Authorizer — emite um token JWT para usuários válidos.

Fonte de usuários (em ordem de precedência):
  1. Variável de ambiente USERS_LIST  → JSON inline (ideal para testes locais)
  2. AWS SSM Parameter Store          → parâmetro definido em USERS_PARAM_NAME
                                        (padrão: /lambda-authorize/users)

Formato da lista de usuários:
  [{"name": "Fulano", "email": "fulano@exemplo.com", "senha": "<md5-da-senha>"}]

Requisição esperada (body JSON):
  {"email": "fulano@exemplo.com", "password": "senha-em-texto-plano"}

Resposta de sucesso (200):
  {"token": "<jwt>"}   — payload contém: name, email, iat, exp
"""

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError
import jwt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_users() -> list[dict]:
    """Carrega a lista de usuários do env var ou do SSM Parameter Store."""
    users_json = os.environ.get("USERS_LIST")
    if users_json:
        return json.loads(users_json)

    param_name = os.environ.get("USERS_PARAM_NAME", "/lambda-authorize/users")
    region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))

    ssm = boto3.client("ssm", region_name=region)
    response = ssm.get_parameter(Name=param_name, WithDecryption=True)
    return json.loads(response["Parameter"]["Value"])


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _build_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def lambda_handler(event: dict, context) -> dict:  # noqa: ANN001
    # --- Parse body ---
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _build_response(400, {"error": "Corpo da requisição inválido (JSON esperado)"})

    email: str = (body.get("email") or "").strip().lower()
    password: str = body.get("password") or ""

    if not email or not password:
        return _build_response(400, {"error": "Os campos 'email' e 'password' são obrigatórios"})

    # --- Carregar usuários ---
    try:
        users = _get_users()
    except (BotoCoreError, ClientError) as exc:
        return _build_response(500, {"error": f"Não foi possível carregar os usuários: {exc}"})
    except (json.JSONDecodeError, ValueError) as exc:
        return _build_response(500, {"error": f"Lista de usuários malformada: {exc}"})

    # --- Validar credenciais ---
    password_hash = _md5(password)
    user = next(
        (
            u for u in users
            if u.get("email", "").strip().lower() == email
            and u.get("senha") == password_hash
        ),
        None,
    )

    if user is None:
        return _build_response(401, {"error": "Credenciais inválidas"})

    # --- Emitir token JWT ---
    secret = os.environ.get("JWT_SECRET", "change-me-in-production")
    expiration_hours = int(os.environ.get("JWT_EXPIRATION_HOURS", "1"))

    now = datetime.now(timezone.utc)
    payload = {
        "name": user["name"],
        "email": user["email"],
        "iat": now,
        "exp": now + timedelta(hours=expiration_hours),
    }

    token = jwt.encode(payload, secret, algorithm="HS256")

    return _build_response(200, {"token": token})

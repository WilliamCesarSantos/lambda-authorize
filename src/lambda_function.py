"""
Lambda Authorizer — emite um token JWT assinado com RS256 para usuários válidos.

Endpoints:
  POST /token      — autentica e retorna um JWT assinado com chave privada RSA
  GET  /public-key — retorna a chave pública (PEM) para verificação do token

Fonte de usuários (em ordem de precedência):
  1. Variável de ambiente USERS_LIST  → JSON inline (ideal para testes locais rápidos)
  2. AWS SSM Parameter Store          → parâmetro definido em USERS_PARAM_NAME
                                        (padrão: /lambda-authorize/users)

Formato da lista de usuários:
  [{"name": "Fulano", "email": "fulano@exemplo.com", "senha": "<hash-md5>"}]

Requisição de autenticação (body JSON):
  {"email": "fulano@exemplo.com", "password": "senha-em-texto-plano"}

Resposta de sucesso (200):
  {"token": "<jwt-rs256>"}   — payload contém: name, email, iat, exp
"""

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL")

    ssm = boto3.client("ssm", region_name=region, endpoint_url=endpoint_url)
    response = ssm.get_parameter(Name=param_name, WithDecryption=True)
    return json.loads(response["Parameter"]["Value"])


def _load_key(env_var: str, default_path: str) -> bytes:
    """Lê uma chave PEM do caminho definido em env_var ou do caminho padrão."""
    key_path = os.environ.get(env_var, default_path)
    return Path(key_path).read_bytes()


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()  # noqa: S324


def _build_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _get_http_method(event: dict) -> str:
    """Extrai o método HTTP de eventos API Gateway v1, v2 ou invocação direta."""
    return (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
        or "POST"
    ).upper()


def _get_path(event: dict) -> str:
    """Extrai o path de eventos API Gateway v1, v2 ou invocação direta."""
    return event.get("path") or event.get("rawPath") or "/"


# ---------------------------------------------------------------------------
# Handlers por endpoint
# ---------------------------------------------------------------------------

def _handle_public_key() -> dict:
    """Retorna a chave pública RSA em formato PEM."""
    try:
        public_key_pem = _load_key(
            "JWT_PUBLIC_KEY_PATH", "/var/task/certs/public.pem"
        ).decode("utf-8")
    except (FileNotFoundError, OSError) as exc:
        return _build_response(500, {"error": f"Chave pública não encontrada: {exc}"})

    return _build_response(200, {"publicKey": public_key_pem})


def _handle_token(event: dict) -> dict:
    """Autentica o usuário e emite um token JWT RS256."""
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

    # --- Carregar chave privada RSA ---
    try:
        private_key = _load_key("JWT_PRIVATE_KEY_PATH", "/var/task/certs/private.pem")
    except (FileNotFoundError, OSError) as exc:
        return _build_response(500, {"error": f"Chave privada não encontrada: {exc}"})

    # --- Emitir token JWT RS256 ---
    expiration_hours = int(os.environ.get("JWT_EXPIRATION_HOURS", "1"))
    now = datetime.now(timezone.utc)
    payload = {
        "name": user["name"],
        "email": user["email"],
        "iat": now,
        "exp": now + timedelta(hours=expiration_hours),
    }

    token = jwt.encode(payload, private_key, algorithm="RS256")
    return _build_response(200, {"token": token})


# ---------------------------------------------------------------------------
# Handler principal
# ---------------------------------------------------------------------------

def lambda_handler(event: dict, context) -> dict:  # noqa: ANN001
    method = _get_http_method(event)
    path = _get_path(event)

    if method == "GET" and path.rstrip("/") in ("/public-key", "/publickey"):
        return _handle_public_key()

    return _handle_token(event)

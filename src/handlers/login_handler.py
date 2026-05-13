"""Login handler — POST /login."""

import json

from botocore.exceptions import BotoCoreError, ClientError

from db.connection import get_connection
from repositories import user_repository
from services import password_service, secrets_service, token_service


def _build_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def handle(event: dict) -> dict:
    """Authenticate user and return a signed JWT."""
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _build_response(400, {"error": "Corpo da requisição inválido (JSON esperado)"})

    email: str = (body.get("email") or "").strip().lower()
    password: str = body.get("password") or ""

    if not email or not password:
        return _build_response(400, {"error": "Os campos 'email' e 'password' são obrigatórios"})

    try:
        conn = get_connection()
    except Exception as exc:
        return _build_response(500, {"error": f"Erro ao conectar ao banco de dados: {exc}"})

    try:
        user = user_repository.find_by_email(conn, email)
    except Exception as exc:
        conn.close()
        return _build_response(500, {"error": f"Erro ao buscar usuário: {exc}"})
    finally:
        conn.close()

    if user is None:
        return _build_response(401, {"error": "Credenciais inválidas"})

    try:
        pepper = secrets_service.get_pepper()
    except (BotoCoreError, ClientError) as exc:
        return _build_response(500, {"error": f"Erro ao buscar configuração: {exc}"})

    if not password_service.verify(password, user.password_hash, pepper):
        return _build_response(401, {"error": "Credenciais inválidas"})

    try:
        token = token_service.issue(
            {"id": user.id, "name": user.name, "email": user.email, "roles": user.roles}
        )
    except (BotoCoreError, ClientError) as exc:
        return _build_response(500, {"error": f"Erro ao emitir token: {exc}"})

    return _build_response(200, {"token": token})

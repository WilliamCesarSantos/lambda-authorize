"""AWS Secrets Manager service — fetches secrets with in-memory caching."""

import os

import boto3

_cache: dict[str, str] = {}


def _get_secret(secret_name: str) -> str:
    if secret_name in _cache:
        return _cache[secret_name]

    region = os.environ.get("AWS_REGION", "sa-east-1")
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL")

    client = boto3.client(
        "secretsmanager",
        region_name=region,
        endpoint_url=endpoint_url,
    )
    response = client.get_secret_value(SecretId=secret_name)
    value: str = response["SecretString"]
    _cache[secret_name] = value
    return value


def get_pepper() -> str:
    name = os.environ.get("PEPPER_SECRET_NAME", "/lambda-authorize/pepper")
    return _get_secret(name)


def get_private_key() -> str:
    name = os.environ.get("PRIVATE_KEY_SECRET_NAME", "/lambda-authorize/private-key")
    return _get_secret(name)


def get_public_key() -> str:
    name = os.environ.get("PUBLIC_KEY_SECRET_NAME", "/lambda-authorize/public-key")
    return _get_secret(name)

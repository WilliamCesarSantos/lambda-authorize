"""Database connection helper."""

import os

import psycopg


def get_connection() -> psycopg.Connection:
    """Open and return a psycopg3 connection using environment variables."""
    return psycopg.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "lambdaauth"),
        user=os.environ.get("DB_USER", "lambda"),
        password=os.environ.get("DB_PASSWORD", "lambda"),
    )

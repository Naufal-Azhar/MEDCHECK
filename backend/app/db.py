"""Small database connection helper for the modular monolith."""

import os

import psycopg


def database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://forgehacks:forgehacks_dev@localhost:5433/forgehacks",
    ).replace("postgresql+psycopg://", "postgresql://", 1)


def connect():
    return psycopg.connect(database_url(), connect_timeout=10)

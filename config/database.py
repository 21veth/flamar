import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


# Lee el archivo .env dentro de config.
load_dotenv(Path(__file__).resolve().parent / ".env")


def obtener_conexion():
    """Abre una conexión con PostgreSQL."""
    password = os.getenv("DB_PASSWORD")

    if not password:
        raise ValueError("Falta DB_PASSWORD en config/.env.")

    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "flamar"),
        user=os.getenv("DB_USER", "postgres"),
        password=password,
        connect_timeout=5,
    )
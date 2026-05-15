import os

import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    url = os.getenv("LINCIUM_DB_URL")
    if not url:
        raise RuntimeError("LINCIUM_DB_URL não configurado")
    return psycopg2.connect(url, cursor_factory=RealDictCursor)


def db_available() -> bool:
    try:
        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False
